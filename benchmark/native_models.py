"""Original mini-swe-agent models, explicit native routes, and nonsecret auditing.

Codex uses the OpenAI Responses protocol through an operator-verified loopback
OAuth bridge. LiteLLM's chatgpt provider is deliberately not used: it injects
instructions, discovers token files, and drops output-token limits. Anthropic
uses LiteLLM's native Messages transport through the user-authorized bridge.
Devin uses OpenAI Chat through the operator-verified loopback CLIProxyAPI bridge.
No bridge route is ready until its exact protocol and settings pass a real gate.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import math
import os
import re
import socket
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

LITELLM_VERSION = "1.102.1"
PROVIDERS = {"go", "vercel", "nim", "google", "devin", "anthropic_oauth", "codex_oauth", "openai", "anthropic", "custom"}
BRIDGE_PROVIDERS = {"devin", "anthropic_oauth", "codex_oauth"}
# Protocol selection controls the native SDK, never a provider-name heuristic.
PROTOCOLS = {"go": {"chat", "responses", "messages"}, "vercel": {"chat", "responses"}, "nim": {"chat"},
             "google": {"chat"}, "devin": {"chat"}, "anthropic_oauth": {"messages"}, "codex_oauth": {"responses"},
             "openai": {"chat", "responses"}, "anthropic": {"messages"},
             "custom": {"chat", "responses", "messages"}}
# LiteLLM provider prefix per route; Google AI Studio uses LiteLLM's native Gemini provider
# (generateContent), never an OpenAI-compatible shim.
SDK_PREFIX = {"google": "gemini"}
GOOGLE_BASE = "https://generativelanguage.googleapis.com/v1beta"
# Gemini 3.x thinkingLevel values (Google thinking docs); LiteLLM maps reasoning_effort onto them.
GOOGLE_EFFORTS = {"minimal", "low", "medium", "high"}
EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}
# A declared tier is the exact reasoning control a model runs at: an effort level,
# "thinking-on" (boolean thinking switch), "thinking-budget" (budget-only thinking) or
# "none-available" (the exact model exposes no reasoning control). Nothing else is accepted.
TIERS = (EFFORTS - {"none"}) | {"none-available", "thinking-on", "thinking-budget"}
ANTHROPIC_EFFORTS = {"low", "medium", "high", "xhigh", "max"}
REASONING_FIELDS = {"chat": ("reasoning_effort", "extra_body"), "responses": ("reasoning",),
                    "messages": ("thinking", "output_config")}
# The OpenAI SDK's raw extra_body pass-through carries NIM chat template switches. LiteLLM's
# Anthropic handler would send an "extra_body" key literally, so Messages never uses it.
EXTRA_BODY = {("nim", "chat"): {"chat_template_kwargs"}}
# Boolean NIM chat-template switches documented on the model cards (force_nonempty_content
# is required by Nemotron 3 for tool calls); only thinking/enable_thinking select a tier.
TEMPLATE_SWITCHES = {"thinking", "enable_thinking", "clear_thinking", "force_nonempty_content"}
# Route-specific declarations for capabilities missing from the pinned SDK's model map.
# OpenCode Go serves these Qwen models on Messages with output_config effort xhigh. Devin
# Chat's exact GPT aliases advertise xhigh in the Devin catalog
# (router-for-me/models devin_models.json), which the pinned SDK's model map lacks.
# Registration changes the capability map, not the transmitted request.
CAPABILITY_OVERRIDES = {
    ("go", "messages", "qwen3.8-flash"): {"effort": "xhigh"},
    ("go", "messages", "qwen3.8-max"): {"effort": "xhigh"},
    ("devin", "chat", "devin/gpt-5-4"): {"effort": "xhigh"},
    ("devin", "chat", "devin/gpt-5-4-mini"): {"effort": "xhigh"},
    ("devin", "chat", "devin/gpt-5-3-codex"): {"effort": "xhigh"},
}
# The OpenAI SDK adds refusal=None to Chat replies. LiteLLM serializes it into
# provider_specific_fields, which these strict Go endpoints reject on the next turn.
# Drop only that synthesized value from outgoing copies; retain native history.
HISTORY_KEY_REMOVALS = {
    ("go", "chat", "glm-5.2"): {"role": "assistant", "key": "provider_specific_fields",
                                "value": {"refusal": None}},
    ("go", "chat", "glm-5.3"): {"role": "assistant", "key": "provider_specific_fields",
                                "value": {"refusal": None}},
}
HISTORY_KEY_REMOVAL_MODEL = "GoStrictHistoryLitellmModel"
WIRE_GENERATION_FIELDS = (
    "max_tokens", "max_completion_tokens", "max_output_tokens", "temperature",
    "reasoning_effort", "reasoning", "thinking", "output_config", "chat_template_kwargs",
    "thinkingConfig",
)
OBSERVATION = (
    "{% if output.get('exception_info') %}<exception>{{output.exception_info}}</exception>\n{% endif %}"
    "<returncode>{{output.returncode}}</returncode>\n<output>\n{{output.output}}</output>"
    "{% if wall_time_limit_seconds > 0 %}\n<time_left>"
    "{{ ([0, (wall_time_limit_seconds - elapsed_seconds) / 60] | max) | int }} min"
    "</time_left>{% endif %}"
)
# native.retries: LiteLLM transport-only retries per HTTP request (transport_retry_policy).
# mini-swe-agent's own query retry is always off, so a failed request never re-enters the agent.
MAX_TRANSPORT_RETRIES = 2
# Retried error classes after LiteLLM 1.102.1 exception mapping: timeouts, 500 (connection
# resets/drops map here) and 503. 4xx classes and unmapped errors (502 BadGateway, generic
# APIError such as funds failures) get 0. LiteLLM gates entry into its retry loop on the
# first error's class; inside the loop it re-sends up to the bound whatever fails next.
RETRIED_ERRORS = ("TimeoutErrorRetries", "InternalServerErrorRetries", "ServiceUnavailableErrorRetries")
NEVER_RETRIED_ERRORS = ("BadRequestErrorRetries", "AuthenticationErrorRetries", "RateLimitErrorRetries",
                        "ContentPolicyViolationErrorRetries", "DefaultRetries")
# Provider response bodies indicating depleted funds or usage windows.
QUOTA_MARKERS = ("insufficient account funds", "usage limit exceeded", "gousagelimiterror",
                 "positive credit balance")
# mini renders this on a reply without a valid tool call; finish_reason "length" (Chat/Messages
# max_tokens, Responses incomplete max_output_tokens) means the output cap cut the reply off.
FORMAT_ERROR = (
    "{{ error }}{% if finish_reason == 'length' %} Your previous reply was cut off at the output "
    "token limit before it contained a complete tool call.{% endif %}"
)


def transport_retry_policy(retries: int) -> dict:
    """LiteLLM RetryPolicy fields: `retries` for transport classes, 0 for everything else."""
    return {**{key: retries for key in RETRIED_ERRORS}, **{key: 0 for key in NEVER_RETRIED_ERRORS}}


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def validate_url(url: str, provider: str | None = None, api: str | None = None) -> str:
    """Validate the declared public route or the user's explicit loopback credential bridge."""
    if not isinstance(url, str):
        raise ValueError("Model base_url must be a string")
    if re.search(r"[\s\\\x00-\x1f\x7f]", url):
        raise ValueError("Model base_url must not contain whitespace, control characters or backslashes")
    try:
        u = urlsplit(url)
        port = u.port
    except ValueError:
        raise ValueError("Invalid model base_url") from None
    if u.username is not None or u.password is not None or "?" in url or "#" in url:
        raise ValueError("Model base_url must not contain credentials, queries or fragments")
    path = u.path.rstrip("/")
    if provider is None or provider in BRIDGE_PROVIDERS:
        if u.scheme != "http" or u.hostname != "127.0.0.1" or not port:
            raise ValueError("Credential bridge must use explicit http://127.0.0.1:PORT")
        if path != "/v1":
            raise ValueError("Credential bridge base_url must end in /v1")
    elif provider in {"go", "vercel", "nim", "google", "openai", "anthropic"}:
        expected = {
            "go": ("opencode.ai", "/zen/go/v1"),
            "vercel": ("ai-gateway.vercel.sh", "/v1"),
            "nim": ("integrate.api.nvidia.com", "/v1"),
            "google": ("generativelanguage.googleapis.com", "/v1beta"),
            "openai": ("api.openai.com", "/v1"),
            "anthropic": ("api.anthropic.com", "/v1"),
        }[provider]
        if (u.scheme, u.hostname, port, path) != ("https", expected[0], None, expected[1]):
            raise ValueError(f"{provider} requires https://{expected[0]}{expected[1]}")
    elif provider == "custom":
        host = u.hostname or ""
        if (u.scheme != "https" or not host or "%" in url
                or re.search(r"(?:sk-|oc_sk_)[A-Za-z0-9_-]{12,}", path, re.I)):
            raise ValueError("Custom base_url must be public HTTPS without encoded or credential-bearing paths")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if (not re.fullmatch(r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
                                 r"[A-Za-z](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", host)
                    or host.endswith((".local", ".internal", ".localhost", ".test", ".invalid", ".lan",
                                      ".home", ".localdomain", ".onion"))
                    or host == "localhost"):
                raise ValueError("Custom base_url must use a public hostname or public IP address")
        else:
            if not public_address(address):
                raise ValueError("Custom base_url must not use a private or nonpublic IP address")
        if api == "messages" and not path.endswith("/v1"):
            raise ValueError("Custom Messages base_url must end in /v1")
    else:
        raise ValueError("Unsupported model provider")
    return url.rstrip("/")


def public_address(address) -> bool:
    """Reject IPv4-mapped private destinations as well as non-global addresses."""
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    return address.is_global and not address.is_multicast


def check_custom_destination(model: dict) -> None:
    """Check resolved addresses before a custom route receives its controller credential."""
    if model["provider"] != "custom":
        return
    url = urlsplit(validate_url(model["base_url"], "custom", model["api"]))
    try:
        addresses = socket.getaddrinfo(url.hostname, url.port or 443, type=socket.SOCK_STREAM)
    except OSError:
        raise ValueError("Custom endpoint DNS resolution failed") from None
    if not addresses or any(not public_address(ipaddress.ip_address(item[4][0])) for item in addresses):
        raise ValueError("Custom endpoint resolves to a private or nonpublic destination")


def _native(config: dict) -> dict:
    value = config.get("native")
    if not isinstance(value, dict) or set(value) != {"timeout_seconds", "retries"}:
        raise ValueError("native requires exactly timeout_seconds and retries")
    timeout, retries = value["timeout_seconds"], value["retries"]
    if type(timeout) not in {int, float} or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("native.timeout_seconds must be finite and positive")
    if type(retries) is not int or not 0 <= retries <= MAX_TRANSPORT_RETRIES:
        raise ValueError(f"native.retries must be an integer between 0 and {MAX_TRANSPORT_RETRIES} (transport-only)")
    return value


def sdk_prefix(model: dict) -> str:
    """LiteLLM provider prefix of the native constructor for this route."""
    return SDK_PREFIX.get(model.get("provider"), "anthropic" if model.get("api") == "messages" else "openai")


def credential_target(model: dict) -> str:
    """The SDK's canonical credential variable for this route (e.g. GEMINI_API_KEY)."""
    return f"{sdk_prefix(model).upper()}_API_KEY"


def transmitted_reasoning(model: dict) -> dict:
    """Reasoning wire fields as sent: SDK extra_body entries become top-level body fields.

    Google: LiteLLM's native Gemini provider sends reasoning_effort as
    generationConfig.thinkingConfig {thinkingLevel, includeThoughts}.
    """
    generation = model["generation"]
    if model.get("provider") == "google":
        effort = generation.get("reasoning_effort")
        return {} if effort is None else {"thinkingConfig": {"thinkingLevel": effort, "includeThoughts": True}}
    wire = {key: generation[key] for key in REASONING_FIELDS[model["api"]]
            if key in generation and key != "extra_body"}
    extra = generation.get("extra_body")
    return wire | extra if isinstance(extra, dict) else wire


def generation_tier(api: str, generation: dict) -> str | None:
    """Return the tier implied by a generation's reasoning control, or None if undeclarable."""
    wire = transmitted_reasoning({"api": api, "generation": generation})
    if not wire:
        return "none-available"
    if api == "chat":
        template = wire.get("chat_template_kwargs") or {}
        effort = wire.get("reasoning_effort", template.get("reasoning_effort"))
        if effort is None and (template.get("thinking") is True or template.get("enable_thinking") is True):
            effort = "thinking-on"
    elif api == "responses":
        effort = wire["reasoning"].get("effort")
    else:
        effort = (wire.get("output_config") or {}).get("effort")
        if effort is None and (wire.get("thinking") or {}).get("type") == "enabled":
            effort = "thinking-budget"
    return effort if effort in TIERS - {"none-available"} else None


def declared_reasoning(model: dict) -> dict:
    """The reasoning fields exactly as declared in generation (tier-spec form)."""
    return {key: model["generation"][key] for key in REASONING_FIELDS[model["api"]]
            if key in model["generation"]}


def check_tier(model: dict) -> str:
    """Fail closed unless the declared tier exactly matches the generation's reasoning control."""
    tier = model.get("tier")
    if (not isinstance(tier, dict) or set(tier) != {"level", "reasoning", "spec_sha256"}
            or tier["level"] not in TIERS
            or not isinstance(tier["spec_sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", tier["spec_sha256"])):
        raise ValueError("Declare tier {level, reasoning, spec_sha256} from the tier spec; undeclared tiers are rejected")
    implied = generation_tier(model["api"], model["generation"])
    if implied != tier["level"] or tier["reasoning"] != declared_reasoning(model):
        raise ValueError("Generation reasoning control differs from the declared tier")
    return tier["level"]


def _check_output_config(output: Any) -> None:
    if (not isinstance(output, dict) or set(output) != {"effort"}
            or not isinstance(output["effort"], str) or output["effort"] not in ANTHROPIC_EFFORTS):
        raise ValueError("output_config must contain one supported Anthropic effort")


def _check_thinking(thinking: Any, max_tokens: int) -> None:
    if thinking == {"type": "adaptive"}:
        return
    if (not isinstance(thinking, dict) or set(thinking) != {"type", "budget_tokens"}
            or thinking["type"] != "enabled" or type(thinking["budget_tokens"]) is not int
            or not 1024 <= thinking["budget_tokens"] < max_tokens):
        raise ValueError("thinking requires adaptive or an enabled budget below max_tokens")


def _check_extra_body(model: dict, extra: Any) -> None:
    allowed = EXTRA_BODY.get((model["provider"], model["api"]))
    if allowed is None:
        raise ValueError("extra_body pass-through is only approved for NIM Chat")
    if not isinstance(extra, dict) or not extra or set(extra) - allowed:
        raise ValueError("extra_body may contain only this route's approved reasoning fields")
    template = extra["chat_template_kwargs"]
    if not isinstance(template, dict) or not template or set(template) - TEMPLATE_SWITCHES - {"reasoning_effort"}:
        raise ValueError("chat_template_kwargs may contain only thinking switches and reasoning_effort")
    if any(type(template[key]) is not bool for key in TEMPLATE_SWITCHES & template.keys()):
        raise ValueError("chat_template_kwargs thinking switches must be booleans")
    if "reasoning_effort" in template and template["reasoning_effort"] not in EFFORTS:
        raise ValueError("Unsupported chat_template_kwargs reasoning_effort")


def _generation(model: dict) -> dict:
    api = model["api"]
    value = model.get("generation")
    allowed = {
        "chat": {"max_tokens", "max_completion_tokens", "temperature", "reasoning_effort", "extra_body"},
        "responses": {"max_output_tokens", "temperature", "reasoning"},
        # Anthropic effort is declared in its wire form so declared equals transmitted.
        "messages": {"max_tokens", "temperature", "thinking", "output_config"},
    }[api]
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError("Unsupported native generation parameters")
    digest(value)
    for key in {"max_tokens", "max_completion_tokens", "max_output_tokens"} & value.keys():
        if type(value[key]) is not int or value[key] < (16 if api == "responses" else 1):
            raise ValueError(f"{key} must be a positive integer (Responses minimum is 16)")
    if api == "chat" and {"max_tokens", "max_completion_tokens"} <= value.keys():
        raise ValueError("Declare only one chat output-token limit")
    if api == "messages" and "max_tokens" not in value:
        raise ValueError("Anthropic Messages requires explicit max_tokens")
    if "temperature" in value and (type(value["temperature"]) not in {int, float}
                                    or not 0 <= value["temperature"] <= 2):
        raise ValueError("temperature must be finite and between 0 and 2")
    if "reasoning_effort" in value and (not isinstance(value["reasoning_effort"], str)
                                      or value["reasoning_effort"] not in EFFORTS):
        raise ValueError("Unsupported reasoning_effort")
    if "reasoning" in value:
        reasoning = value["reasoning"]
        if (not isinstance(reasoning, dict) or set(reasoning) != {"effort"}
                or not isinstance(reasoning["effort"], str) or reasoning["effort"] not in EFFORTS):
            raise ValueError("reasoning must contain one supported effort")
    if "output_config" in value:
        _check_output_config(value["output_config"])
    if "thinking" in value:
        _check_thinking(value["thinking"], value["max_tokens"])
    if "extra_body" in value:
        _check_extra_body(model, value["extra_body"])
    if "reasoning_effort" in value and "chat_template_kwargs" in value.get("extra_body", {}):
        raise ValueError("Declare one NIM reasoning control: top-level reasoning_effort or chat_template_kwargs")
    if model.get("provider") == "google":
        # Gemini: one output cap and one thinkingLevel effort; nothing else is declared.
        if set(value) - {"max_tokens", "reasoning_effort"} or "max_tokens" not in value:
            raise ValueError("Google routes declare exactly max_tokens and optionally reasoning_effort")
        if "reasoning_effort" in value and value["reasoning_effort"] not in GOOGLE_EFFORTS:
            raise ValueError("Gemini thinkingLevel supports only minimal, low, medium and high")
    check_tier(model)
    # The native converter must not silently cap, translate or drop declared settings.
    mapped = _map_generation(model, value)
    wire = mapped | mapped.get("extra_body", {})
    if any(wire.get(key) != declared for key, declared in transmitted_reasoning(model).items()):
        raise ValueError("Native SDK would alter or drop the declared reasoning control")
    if model.get("provider") == "google" and wire.get("max_output_tokens") != value["max_tokens"]:
        raise ValueError("Native Gemini SDK would not transmit the declared output cap")
    if model.get("provider") == "devin":
        for key in {"max_tokens", "max_completion_tokens"} & value.keys():
            if wire.get(key) != value[key]:
                raise ValueError("Native Devin Chat SDK would alter or drop the declared output cap")
    if api == "messages":
        thinking = wire.get("thinking")
        if isinstance(thinking, dict) and thinking.get("type") == "enabled":
            if thinking.get("budget_tokens", 0) >= value["max_tokens"]:
                raise ValueError("Effective thinking budget must be below max_tokens")
    return mapped


def _litellm():
    # LiteLLM otherwise searches for an ambient .env even with a clean HOME.
    os.environ["LITELLM_MODE"] = "PRODUCTION"
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    import importlib.metadata
    if importlib.metadata.version("litellm") != LITELLM_VERSION:
        raise RuntimeError(f"Native integration requires LiteLLM {LITELLM_VERSION}")
    import litellm
    litellm.drop_params = False
    litellm.suppress_debug_info = True
    litellm.set_verbose = False
    for name in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy", "httpx", "httpcore", "openai",
                 "litellm_model", "litellm_response_model", "minisweagent", "agent"):
        logging.getLogger(name).disabled = True
    return litellm


def sdk_controls(model: dict) -> dict:
    """SDK-only opt-ins (never wire fields) a declared generation needs to be sent unaltered.

    LiteLLM accepts Anthropic thinking only for Claude names unless the caller opts in with
    its documented allowed_openai_params flag. Go and custom Messages may serve other models.
    """
    if model["provider"] in {"go", "custom"} and model["api"] == "messages" and "thinking" in model["generation"]:
        return {"allowed_openai_params": ["thinking"]}
    return {}


def capability_override(model: dict) -> dict | None:
    """The declared SDK capability for this exact route, or None.

    A declared name on another route, or at another effort, is rejected rather
    than run with the name's registry entry.
    """
    override = CAPABILITY_OVERRIDES.get((model["provider"], model["api"], model["model"]))
    if override is None:
        if model["model"] in {name for _, _, name in CAPABILITY_OVERRIDES}:
            raise ValueError("Capability override is approved only for its exact provider route")
        return None
    control = ("reasoning_effort", override["effort"]) if model["api"] == "chat" else (
        "output_config", {"effort": override["effort"]})
    if model["generation"].get(control[0]) != control[1] or model["tier"]["level"] != override["effort"]:
        raise ValueError("Capability override covers only its declared reasoning effort")
    return override


def remove_synthesized_key(message: dict, removal: dict) -> dict:
    """An outgoing copy of `message` without the declared SDK-synthesized key; never mutates history.

    Any other value under that key came from somewhere else and is not dropped silently.
    """
    value = message.get(removal["key"])
    if message.get("role") != removal["role"] or value is None:
        return message
    if value != removal["value"]:
        raise ValueError(f"{removal['key']} carries data beyond the SDK-synthesized value; not removing it")
    return {key: item for key, item in message.items() if key != removal["key"]}



def _register_capability_override(llm, model: dict) -> None:
    """Declare the approved effort capability in LiteLLM's model registry for this exact name."""
    override = capability_override(model)
    if override is None:
        return
    name = model["model"]
    entry = {"litellm_provider": sdk_prefix(model), "mode": "chat",
             f"supports_{override['effort']}_reasoning_effort": True}

    def registered() -> bool:
        current = llm.model_cost.get(name)
        return isinstance(current, dict) and all(current.get(k) == v for k, v in entry.items())

    # register_model merges SDK model-info defaults into the entry, so compare the declaration.
    if name in llm.model_cost and not registered():
        raise ValueError("Capability override would replace an existing LiteLLM model-map entry")
    llm.utils.register_model({name: entry})
    if not registered():
        raise ValueError("LiteLLM did not register the declared capability")


def _map_generation(model: dict, value: dict) -> dict:
    llm = _litellm()
    name = model["model"]
    _register_capability_override(llm, model)
    if model["api"] == "responses":
        from litellm.llms.openai.responses.transformation import OpenAIResponsesAPIConfig
        return OpenAIResponsesAPIConfig().map_openai_params(value, name, drop_params=False)
    mapped = llm.utils.get_optional_params(
        model=name, custom_llm_provider=sdk_prefix(model),
        drop_params=False, **value, **sdk_controls(model),
    )
    if model.get("provider") == "google":
        mapped = {key: item for key, item in mapped.items() if item is not None}
    if model["api"] == "messages" and "output_config" in mapped:
        # Run the SDK's own request-time output_config gate now, not mid-campaign.
        from litellm.llms.anthropic.chat.transformation import AnthropicConfig
        data = {}
        try:
            AnthropicConfig()._apply_output_config(data=data, model=name, optional_params=dict(mapped))
        except Exception as exc:
            raise ValueError("Native Anthropic SDK rejects the declared output_config effort for this model") from exc
        if data.get("output_config") != mapped["output_config"]:
            raise ValueError("Native Anthropic SDK would not transmit the declared output_config")
    return mapped


def validate_model(config: dict, model: dict) -> dict:
    """Return auditable effective settings without resolving any credential."""
    native = _native(config)
    allowed = {"id", "model", "response_model", "provider", "api", "base_url", "api_key_env",
               "generation", "tier", "readiness", "inventory_id", "effective_settings", "backend_provenance"}
    if set(model) - allowed:
        raise ValueError("Unsupported model fields; credentials and native overrides are forbidden")
    provider = model.get("provider")
    api = model.get("api")
    if provider not in PROVIDERS:
        raise ValueError("Unsupported provider; declare a direct API, custom service or user-authorized bridge route")
    if api not in {"chat", "responses", "messages"}:
        raise ValueError("Model api must be chat, responses or messages")
    if api not in PROTOCOLS[provider]:
        raise ValueError("Route must use its provider's original native protocol")
    for key in ("model", "response_model"):
        if not isinstance(model.get(key), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", model[key]):
            raise ValueError(f"Declare an exact {key} identifier")
    env = model.get("api_key_env")
    if not isinstance(env, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", env):
        raise ValueError("api_key_env must name an environment variable, not contain a credential")
    base = validate_url(model.get("base_url"), provider, api)
    effective_generation = _generation(model)
    if api == "chat" and provider != "google":
        # The pinned SDK silently reroutes some Chat requests (e.g. GPT-5.4+ with tools and
        # reasoning) to /responses. The declared protocol must be the transmitted one.
        from litellm.main import responses_api_bridge_check
        bridged, _ = responses_api_bridge_check(
            model=model["model"], custom_llm_provider="openai",
            tools=[{"type": "function", "function": {"name": "bash"}}],
            reasoning_effort=model["generation"].get("reasoning_effort"), api_base=base)
        if bridged.get("mode") == "responses":
            raise ValueError("Native SDK would reroute this Chat route to Responses; declare the Responses protocol")
    prefix = sdk_prefix(model)
    # retry_policy is LiteLLM's own per-exception retry configuration (a LiteLLM-only
    # parameter, never sent on the wire); the OpenAI client's max_retries stays 0.
    kwargs = {"api_base": base, "timeout": native["timeout_seconds"], "max_retries": 0,
              "retry_policy": transport_retry_policy(native["retries"]),
              "drop_params": False, **model["generation"], **sdk_controls(model)}
    if api == "messages":
        # LiteLLM 1.102.1 appends /v1/messages, not /messages, to api_base.
        # Keep the declared route canonical (/v1), but pass its origin to the SDK.
        kwargs["api_base"] = base.removesuffix("/v1")
    if api == "responses":
        kwargs["store"] = False
        if provider == "codex_oauth":
            kwargs["include"] = ["reasoning.encrypted_content"]
    if provider == "google":
        # LiteLLM's Gemini provider builds the generateContent URL itself from GOOGLE_BASE;
        # a custom api_base would change its URL construction, so none is passed.
        kwargs.pop("api_base")
    if provider == "go":
        kwargs["extra_headers"] = {"User-Agent": "keygen-benchmark/mini-swe-agent-2.4.6"}
    # SDK optional params include transport defaults and an extra_body envelope.
    # Both SDK paths expand extra_body into the wire body; it is not a generation field.
    wire_parameters = effective_generation | effective_generation.get("extra_body", {})
    transmitted_generation = {key: wire_parameters[key] for key in WIRE_GENERATION_FIELDS
                              if key in wire_parameters}
    effective = {
        "model_class": "LitellmResponseModel" if api == "responses" else "LitellmModel",
        "model_name": f"{prefix}/{model['model']}", "model_kwargs": kwargs,
        "requested_generation": model["generation"],
        "declared_tier": model["tier"]["level"],
        "declared_reasoning": declared_reasoning(model),
        "transmitted_reasoning": transmitted_reasoning(model),
        "expected_transmitted_generation": transmitted_generation,
        "delivered_generation": None,
        "settings_evidence": "pinned native SDK transformation only; endpoint delivery remains unverified",
        "sdk_capability_override": capability_override(model),
        "effective_generation": effective_generation,
        "output_limit": next((transmitted_generation[k] for k in
                              ("max_output_tokens", "max_completion_tokens", "max_tokens")
                              if k in transmitted_generation), None),
        "output_limit_enforced": None,  # Provider delivery requires the real payload gate.
        "retry_policy": {"mini_attempts": 1, "sdk_transport_retries": native["retries"],
                         "retried": "timeouts, HTTP 500 (incl. connection resets), HTTP 503",
                         "never_retried": "HTTP 4xx incl. 429 quota/rate limits, 502 and other unmapped errors",
                         "caveat": "LiteLLM gates retries on the first error; a later re-send counts toward the same bound",
                         "recorded_as": "status totals.transport_retries"},
        "cost_policy": "native estimate when positive; zero/missing is unknown, not free",
        "observation_time_left": "every tool result, rendered by original native formatter",
    }
    removal = HISTORY_KEY_REMOVALS.get((provider, api, model["model"]))
    if removal is not None:
        # Only declared routes carry this field; every other route's settings are unchanged.
        effective["history_key_removal"] = {**removal, "model_type": f"native_models.{HISTORY_KEY_REMOVAL_MODEL}"}
    return effective


def credential_env(config: dict, model: dict) -> dict[str, str]:
    """Resolve just this route's key in the trusted controller, never in the VM."""
    validate_model(config, model)
    env_name = model.get("api_key_env")
    if not isinstance(env_name, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", env_name):
        raise ValueError("Invalid credential environment name")
    value = os.environ.get(env_name)
    if not value:
        raise ValueError(f"Missing credential environment variable {env_name}")
    target = credential_target(model)
    return {target: value,
            "MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT": "1",
            "LITELLM_MODE": "PRODUCTION", "LITELLM_LOCAL_MODEL_COST_MAP": "True"}


def redact_credentials(value: Any, secrets: list[str] | tuple[str, ...]) -> Any:
    """Redact SDK exception/response echoes before writing native artifacts."""
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
        return value
    if isinstance(value, dict):
        return {redact_credentials(k, secrets): redact_credentials(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_credentials(v, secrets) for v in value]
    if isinstance(value, tuple):
        return tuple(redact_credentials(v, secrets) for v in value)
    return value


def _usage(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _usage(v) for k, v in value.items() if isinstance(k, str)
                and re.fullmatch(r"[a-z_]{1,80}", k) and isinstance(v, (dict, int, float, type(None)))}
    if type(value) in {int, float} and math.isfinite(value) and value >= 0:
        return value
    return None


def gemini_usage(meta: Any) -> dict | None:
    """Gemini usageMetadata in the OpenAI usage shape the reports read (thinking counts as output)."""
    if not isinstance(meta, dict):
        return None
    number = lambda key: meta.get(key) if type(meta.get(key)) is int else 0
    thoughts = number("thoughtsTokenCount")
    return {"prompt_tokens": number("promptTokenCount"),
            "completion_tokens": number("candidatesTokenCount") + thoughts,
            "total_tokens": number("totalTokenCount"),
            "prompt_tokens_details": {"cached_tokens": number("cachedContentTokenCount")},
            "completion_tokens_details": {"reasoning_tokens": thoughts}}


def _response_audit(raw: dict, model: dict) -> dict:
    error = raw.get("error")
    # Gemini generateContent names the serving model in modelVersion.
    returned = raw.get("model") if "model" in raw else raw.get("modelVersion")
    if not isinstance(returned, str):
        returned = None
    if error is not None or raw.get("type") == "error" or raw.get("status") == "failed":
        status = "gateway_error"
    elif not returned:
        status = "identity_unverified"
    elif returned != model["response_model"]:
        status = "identity_mismatch"
    else:
        status = "identity_match"
    usage = raw.get("usage") if "usage" in raw else gemini_usage(raw.get("usageMetadata"))
    return {"requested_model": model["model"], "expected_response_model": model["response_model"],
            "response_model": returned, "identity_status": status,
            "usage": _usage(usage)}


def audit_messages(messages: list[dict], model: dict) -> list[dict]:
    """Read native extras, including native Responses' top-level response items."""
    result = []
    for index, message in enumerate(messages):
        extra = message.get("extra", {})
        raw = extra.get("response")
        if raw is None and message.get("object") == "response":
            raw = message
        if not isinstance(raw, dict):
            continue
        audit = _response_audit(raw, model)
        cost = extra.get("cost")
        estimated = type(cost) in {int, float} and math.isfinite(cost) and cost > 0
        audit.update(message_index=index, cost=cost if estimated else None,
                     cost_status="native_estimate" if estimated else "unknown")
        result.append(audit)
    return result


def classify_error(error: Exception, run_dir: Path | None = None) -> str:
    """Classify native failures without persisting provider error bodies."""
    name = type(error).__name__
    # Funds/usage-window bodies arrive under several classes (APIError, RateLimitError, even
    # 5xx "server_error"); only the category is returned, the body is never persisted.
    text = str(error).lower()
    if (name in {"RateLimitError", "BudgetExceededError"} or getattr(error, "status_code", None) == 429
            or any(marker in text for marker in QUOTA_MARKERS)):
        return "quota_or_rate_limit"
    if run_dir is not None:
        path = run_dir / "transport.jsonl"
        if path.exists():
            for line in reversed(path.read_text().splitlines()):
                record = json.loads(line)
                if record.get("event") == "request":
                    break  # A newer request failed before a raw response was available.
                if record.get("event") == "response":
                    if record.get("identity_status") == "gateway_error":
                        return "gateway_error"
                    break
    if name in {"AuthenticationError", "PermissionDeniedError"}:
        return "authentication_error"
    if name in {"Timeout", "APITimeoutError", "TimeoutError", "APIConnectionError",
                "ServiceUnavailableError", "InternalServerError"}:
        return "transport_error"
    if name in {"UnsupportedParamsError", "BadRequestError", "NotFoundError"}:
        return "provider_request_error"
    if type(error).__module__.startswith(("litellm", "openai")) or isinstance(error, (AttributeError, ValueError, TypeError, IndexError)):
        return "native_model_error"
    return "infrastructure_error"


def build_model(config: dict, model: dict, run_dir: Path):
    """Construct a production model only after verified native qualification."""
    effective = validate_model(config, model)
    readiness = model.get("readiness")
    if not isinstance(readiness, dict) or readiness.get("status") != "verified":
        raise ValueError("Model requires verified native protocol readiness before execution")
    return _construct_model(config, model, run_dir, effective)


def build_probe_model(config: dict, model: dict, run_dir: Path):
    """Bootstrap real qualification without asserting previous readiness.

    This uses the production constructors, callbacks, parser and native history.
    It is not a production readiness bypass: campaign execution uses build_model.
    """
    return _construct_model(config, model, run_dir, validate_model(config, model))


def _construct_model(config: dict, model: dict, run_dir: Path, effective: dict):
    home = Path(os.environ.get("HOME", ""))
    global_config = Path(os.environ.get("MSWEA_GLOBAL_CONFIG_DIR", ""))
    if (not home.is_absolute() or not global_config.is_absolute()
            or not global_config.is_relative_to(home)
            or (global_config / ".env").exists()
            or os.environ.get("MSWEA_SILENT_STARTUP") != "1"):
        raise RuntimeError("Native models require isolated HOME and empty mini global config")
    check_custom_destination(model)
    target = credential_target(model)
    if not os.environ.get(target):
        raise RuntimeError("Native worker lacks its isolated provider credential")
    if os.environ.get("MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT") != "1":
        raise RuntimeError("Native worker must disable mini-level retries; transport retries are the SDK's")
    llm = _litellm()
    from litellm.integrations.custom_logger import CustomLogger
    from minisweagent.models.litellm_model import LitellmModel
    from minisweagent.models.litellm_response_model import LitellmResponseModel

    class NativeAudit(CustomLogger):
        # This is a supported SDK observability callback, not a model wrapper.
        def __init__(self):
            super().__init__()
            self.lock = threading.Lock()

        def _write(self, record):
            record = redact_credentials(record, [os.environ[target]])
            with self.lock, (run_dir / "transport.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, allow_nan=False) + "\n")

        def log_pre_api_call(self, model, messages, kwargs):
            payload = kwargs.get("additional_args", {}).get("complete_input_dict")
            if not isinstance(payload, dict):
                return
            # The SDK expands an extra_body envelope into the HTTP body; record it as sent.
            # Gemini nests generation settings in generationConfig; record them as sent too.
            extra = payload.get("extra_body")
            body = payload | extra if isinstance(extra, dict) else payload
            config = payload.get("generationConfig")
            body = body | config if isinstance(config, dict) else body
            settings = {k: body[k] for k in WIRE_GENERATION_FIELDS + ("store", "include")
                        if k in body}
            self._write({"event": "request", "model": payload.get("model", model), "settings": settings,
                         "input_sha256": digest(payload.get("messages", payload.get("input", payload.get("contents")))),
                         "tools_sha256": digest(payload.get("tools")),
                         "payload_scope": "controller_to_endpoint",
                         "provider_received_verified": False})

        def log_post_api_call(self, kwargs, response_obj, start_time, end_time):
            raw = kwargs.get("original_response")
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except (ValueError, TypeError):
                    return
            if not isinstance(raw, dict):
                return
            record = _response_audit(raw, model)
            record["event"] = "response"
            if start_time is not None and end_time is not None:
                seconds = (end_time - start_time).total_seconds()
                if math.isfinite(seconds) and seconds >= 0:
                    record["latency_seconds"] = seconds
            self._write(record)

    # A worker hosts one model. No external callbacks, telemetry or mini registry file; an
    # approved capability override was registered by validate_model in this process.
    llm.callbacks = []
    llm.input_callback = [NativeAudit()]
    llm.success_callback = []
    llm.failure_callback = []
    kwargs = effective["model_kwargs"]
    if model["provider"] == "go":
        kwargs["extra_headers"]["x-opencode-session"] = digest(str(run_dir.resolve()))
    cls = LitellmResponseModel if model["api"] == "responses" else LitellmModel
    removal = effective.get("history_key_removal")
    if removal is not None:
        if HISTORY_KEY_REMOVALS.get((model["provider"], model["api"], model["model"])) is None:
            raise ValueError("History key removal is declared only for its exact provider route")

        class GoStrictHistoryLitellmModel(LitellmModel):
            """The original LitellmModel; outgoing copies drop only the declared SDK-synthesized key."""

            def _prepare_messages_for_api(self, messages: list[dict]) -> list[dict]:
                return [remove_synthesized_key(message, removal)
                        for message in super()._prepare_messages_for_api(messages)]

        # Its trajectory model_type names this declared subclass, as effective settings record.
        GoStrictHistoryLitellmModel.__module__ = "native_models"
        cls = GoStrictHistoryLitellmModel
    return cls(model_name=effective["model_name"], model_kwargs=kwargs,
               litellm_model_registry=None, cost_tracking="ignore_errors", set_cache_control=None,
               observation_template=OBSERVATION, format_error_template=FORMAT_ERROR, multimodal_regex="")
