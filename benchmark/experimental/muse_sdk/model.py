"""Opt-in mini model adapter; never a qualified frozen Keygen provider."""
import os
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler

from minisweagent.models.litellm_model import LitellmModel

CONDITION = "muse-sdk-experimental-not-frozen"


class MuseMiniModel(LitellmModel):
    def __init__(self, *, model_name: str, bridge_url: str = "http://127.0.0.1:8321/v1",
                 allow_credit_usage: bool = False, accept_experimental_condition: bool = False):
        if not allow_credit_usage or not accept_experimental_condition:
            raise ValueError("Explicit credit-use and experimental-condition consent required")
        url = urlsplit(bridge_url)
        if (url.scheme != "http" or url.hostname != "127.0.0.1" or not url.port
                or url.username or url.password or url.query or url.fragment or url.path != "/v1"):
            raise ValueError("Bridge must be an explicit loopback HTTP /v1 endpoint")
        if not model_name or model_name.startswith("openai/"):
            raise ValueError("Supply the exact Muse catalogue ID, without a LiteLLM prefix")
        if any(os.environ.get(key) for key in ("MUSE_API_KEY", "META_API_KEY", "MODEL_API_KEY")):
            raise ValueError("Keep provider API credentials out of the mini process; use only the local bridge bearer")
        token = os.environ.get("KEYGEN_MUSE_BRIDGE_TOKEN", "")
        if len(token) < 24:
            raise ValueError("Dedicated local bridge bearer required; no Muse credentials enter mini")
        self._bridge_url = bridge_url
        self._token = token
        # No sampling/output-cap fields: this is an explicitly different condition,
        # not a silently relaxed native_models route. Dollar cost remains unknown.
        super().__init__(model_name=f"openai/{model_name}", cost_tracking="ignore_errors",
                         model_kwargs={"api_base": bridge_url, "api_key": token,
                                       "timeout": 125, "max_retries": 0, "drop_params": False})

    def query(self, messages, **kwargs):
        if kwargs:
            raise ValueError("Experimental Muse route cannot accept generation overrides")
        # mini's retry helper reads this process-level setting at query time.
        # Never silently change it for other concurrently running models.
        if os.environ.get("MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT") != "1":
            raise ValueError("Set MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT=1 explicitly")
        return super().query(messages)

    def _calculate_cost(self, response):
        # Mini requires a numeric accumulator. Zero here is NOT observed free usage.
        self._last_bridge_provenance = response.get("keygen_provenance", {})
        return {"cost": 0.0, "cost_known": False, "condition": CONDITION}

    def get_template_vars(self, **kwargs):
        result = super().get_template_vars(**kwargs)
        result["model_kwargs"].pop("api_key", None)
        return result

    def serialize(self):
        result = super().serialize()
        result["info"]["config"]["model"]["model_kwargs"].pop("api_key", None)
        result["info"]["muse_experiment"] = {
            "condition": CONDITION, "frozen_eligible": False, "cost_known": False,
            "model_identity": "requested-only-unverified", "output_limit_enforced": False,
            "generation": "Muse Code defaults; no equivalence claimed",
            "system_prompt_replaced": False, "auxiliary_inference": "not-excluded",
            "bridge_receipt": getattr(self, "_last_bridge_provenance", {}),
        }
        return result

    def close(self):
        request = Request(self._bridge_url.removesuffix("/v1") + "/close", data=b"",
                          headers={"Authorization": f"Bearer {self._token}"}, method="POST")
        # A literal loopback-only request must not be sent through a remote proxy.
        with build_opener(ProxyHandler({})).open(request, timeout=10) as response:
            response.read()
