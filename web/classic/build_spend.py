"""Build spend.json: list-price spend over every recorded benchmark attempt on every controller.

Each controller is read over SSH (read-only) by a small stdlib collector sent on stdin. The
collector reads only token-usage metadata: attempt status totals, usage fields of trajectory
messages and transport responses, qualification proofs, sanitized public snapshots, and the
same members inside attempt export archives (streamed, never extracted). Copies of one attempt
(archive staging, collected proofs, repo copies, public snapshots) are merged by usage identity.

Usage: python3 web/classic/build_spend.py
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "web/prototype"))
from build import estimate_cost, price_id, public_maker, public_price  # noqa: E402

OUTPUTS = (HERE / "data-src/spend.json", Path("/home/ubuntu/keygen-local-preview/dist/spend.json"))
# (label, ssh target or None for this machine, roots; globs are expanded on the host)
HOSTS = (
    ("ashburn", "ubuntu@100.64.0.10", ["/home/ubuntu/keygen-full.*", "/home/ubuntu/keygen-public-*",
                                          "/home/ubuntu/keygen-web-*"]),
    ("paris", "ubuntu-paris", ["/home/ubuntu/keygen-full.*", "/home/ubuntu/keygen-public-*",
                               "/home/ubuntu/keygen-web-*"]),
    ("local", None, [str(ROOT / "benchmark/runs"), str(ROOT / "legacy"), "/tmp/keygen-web-snapshots-*",
                     "/home/ubuntu/keygen-local-preview/dist"]),
)

COLLECTOR = r'''
import glob, io, json, os, re, sys, tarfile

PRUNE = {"runtime", "node_modules", ".git", ".venv", "site-packages", "__pycache__", "media", "evaluations",
         "submission", "canonical", "test-home", "gdrive", "gdrive2", "lib", "bin", "include"}
SKIP_ARCHIVES = {"native-images.tar"}
MEMBERS = ("status.json", "trajectory.json", "transport.jsonl", "proof.json", "blocker.json",
           "pilot-spec.json", "spec.json")
MAX_BYTES = 512 * 1024 ** 2


ROOT = "/"


def emit(record):
    if "path" in record:
        outer, _, inner = record["path"].partition(":")
        record["rel"] = os.path.relpath(outer, ROOT) + (":" + inner if inner else "")
    sys.stdout.write(json.dumps(record, separators=(",", ":")) + "\n")


def error(path, reason):
    emit({"error": path, "reason": reason})


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def usage_tokens(u):
    """Same fields as benchmark/run.py summarize(); Anthropic-shape cache reads/writes count as input."""
    if not isinstance(u, dict) or not u:
        return None
    if "prompt_tokens" in u:
        prompt = number(u.get("prompt_tokens"))
        cached = number((u.get("prompt_tokens_details") or {}).get("cached_tokens")) or number(
            u.get("cache_read_input_tokens")) or number(u.get("prompt_cache_hit_tokens"))
        completion = number(u.get("completion_tokens"))
    else:
        prompt = number(u.get("input_tokens"))
        if "cache_read_input_tokens" in u or "cache_creation_input_tokens" in u:
            cached = number(u.get("cache_read_input_tokens"))
            prompt += cached + number(u.get("cache_creation_input_tokens"))
        else:
            cached = number((u.get("input_tokens_details") or {}).get("cached_tokens"))
        completion = number(u.get("output_tokens"))
    details = u.get("completion_tokens_details") or u.get("output_tokens_details") or {}
    reasoning = number(details.get("reasoning_tokens")) or number(details.get("thinking_tokens"))
    return prompt, cached, completion, reasoning


def add(sums, tokens):
    if tokens is not None:
        for i, value in enumerate(tokens):
            sums[i] += value
        sums[4] += 1


def from_trajectory(trajectory):
    sums = [0, 0, 0, 0, 0]
    for message in (trajectory or {}).get("messages") or []:
        if not isinstance(message, dict):
            continue
        raw = (message.get("extra") or {}).get("response")
        if raw is None and message.get("object") == "response":
            raw = message
        if isinstance(raw, dict):
            add(sums, usage_tokens(raw.get("usage")))
    return sums


def from_transport(events):
    sums = [0, 0, 0, 0, 0]
    model = None
    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get("event") == "request" and isinstance(event.get("model"), str):
            model = model or event["model"]
        if event.get("event") == "response":
            add(sums, usage_tokens(event.get("usage")))
    return sums, model


def jsonl(text):
    out = []
    for line in text.splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def model_of(status, specs, proof, wire):
    model = (status or {}).get("model")
    if isinstance(model, dict):
        return model.get("inventory_id") or model.get("id") or model.get("model")
    if isinstance(model, str):
        return model
    for spec in specs:
        m = (spec or {}).get("model")
        if isinstance(m, dict) and (m.get("inventory_id") or m.get("id")):
            return m.get("inventory_id") or m.get("id")
    route = (proof or {}).get("route") or {}
    return route.get("inventory_id") or route.get("model") or wire


def provider_of(status, specs, proof):
    """Route the attempt was served by (go, vercel, nim, devin, codex_oauth, ...), from its own metadata."""
    candidates = [(status or {}).get("model")] + [(spec or {}).get("model") for spec in specs] + [(proof or {}).get("route")]
    for model in candidates:
        if isinstance(model, dict) and isinstance(model.get("provider"), str):
            return model["provider"]
    for model in candidates:
        if isinstance(model, dict) and isinstance(model.get("id"), str):
            match = re.match(r"^(codex_oauth|anthropic_oauth|go|vercel|devin|nim)[-/]", model["id"])
            if match:
                return match.group(1)
    return None


def attempt(host, path, files):
    """files: name -> loader returning text or None. Emits at most one record per attempt directory."""
    def load(name):
        try:
            text = files[name]() if name in files else None
            return None if text is None else (jsonl(text) if name.endswith(".jsonl") else json.loads(text))
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            error(path + "/" + name, type(exc).__name__)
            return None
    status = load("status.json") if "status.json" in files else None
    specs = [load(n) for n in ("pilot-spec.json", "spec.json") if n in files]
    sums, source, wire, proof = None, None, None, None
    totals = (status or {}).get("totals") if isinstance((status or {}).get("totals"), dict) else {}
    if status is not None and status.get("status") != "SKIPPED_AFTER_SUCCESS" and any(
            number(totals.get(k)) for k in ("prompt_tokens", "completion_tokens")):
        sums = [number(totals.get(k)) for k in ("prompt_tokens", "cached_tokens", "completion_tokens", "reasoning_tokens")]
        sums.append(number(totals.get("requests")))
        source = "status"
    if sums is None and "trajectory.json" in files:
        candidate = from_trajectory(load("trajectory.json"))
        if candidate[0] or candidate[2]:
            sums, source = candidate, "trajectory"
    if "transport.jsonl" in files and (sums is None or (status is None and not specs)):
        candidate, wire = from_transport(load("transport.jsonl") or [])
        if sums is None and (candidate[0] or candidate[2]):
            sums, source = candidate, "transport"
    for name in ("proof.json", "blocker.json"):
        if sums is None and name in files:
            proof = load(name) or {}
            candidate = from_trajectory(proof.get("trajectory"))
            if not (candidate[0] or candidate[2]):
                candidate, wire = from_transport(proof.get("transport") or [])
            else:
                wire = wire or from_transport(proof.get("transport") or [])[1]
            if candidate[0] or candidate[2]:
                sums, source = candidate, name.split(".")[0]
    record = {"host": host, "path": path, "source": source, "model": model_of(status, specs, proof, wire),
              "provider": provider_of(status, specs, proof),
              "status": (status or {}).get("status"), "exhibition": bool((status or {}).get("exhibition"))}
    if sums is None:
        record.update(tokens=None)
    else:
        record.update(tokens={"prompt": sums[0], "cached": sums[1], "completion": sums[2], "reasoning": sums[3],
                              "requests": sums[4]})
    emit(record)


def published(host, path, document, kind):
    for run in document.get("runs") or []:
        usage = run.get("usage") or {}
        if not (number(usage.get("prompt_tokens")) or number(usage.get("completion_tokens"))):
            continue
        emit({"host": host, "path": path, "source": kind, "model": run.get("model_key") or run.get("name"),
              "status": run.get("status"), "exhibition": bool(run.get("exhibition")), "cost_usd": run.get("cost_usd"),
              "tokens": {"prompt": number(usage.get("prompt_tokens")), "cached": number(usage.get("cached_tokens")),
                         "completion": number(usage.get("completion_tokens")),
                         "reasoning": number(usage.get("reasoning_tokens")), "requests": number(usage.get("requests"))}})


def archive(host, path):
    groups = {}
    try:
        with tarfile.open(path, "r|*") as bundle:
            for member in bundle:
                name = os.path.basename(member.name)
                if not member.isfile() or name not in MEMBERS or name.endswith(".private.json"):
                    continue
                if member.size > MAX_BYTES:
                    error(path + ":" + member.name, "member too large")
                    continue
                text = bundle.extractfile(member).read().decode("utf-8", "replace")
                groups.setdefault(os.path.dirname(member.name), {})[name] = (lambda t=text: t)
    except (OSError, tarfile.TarError, EOFError) as exc:
        error(path, type(exc).__name__)
        return
    for directory, files in sorted(groups.items()):
        if set(files) & {"status.json", "trajectory.json", "transport.jsonl", "proof.json", "blocker.json"}:
            attempt(host, path + ":" + (directory or "."), files)


def reader(path):
    def read():
        if os.path.getsize(path) > MAX_BYTES:
            raise OSError("too large")
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    return read


def main(host, patterns):
    global ROOT
    seen = set()
    for pattern in patterns:
        for root in sorted(glob.glob(pattern)):
            real = os.path.realpath(root)
            if real in seen or not os.path.isdir(real):
                continue
            seen.add(real)
            ROOT = real
            for directory, dirs, names in os.walk(real, onerror=lambda exc: error(str(exc.filename), "unreadable")):
                dirs[:] = sorted(d for d in dirs if d not in PRUNE and not d.startswith(".") and "private" not in d
                                 and not d.endswith("home"))
                names = set(names)
                files = {n: reader(os.path.join(directory, n)) for n in MEMBERS if n in names}
                if set(files) & {"status.json", "trajectory.json", "transport.jsonl", "proof.json", "blocker.json"}:
                    attempt(host, directory, files)
                if "snapshot.json" in names:
                    try:
                        published(host, directory, json.loads(reader(os.path.join(directory, "snapshot.json"))()), "snapshot")
                    except (OSError, ValueError) as exc:
                        error(directory + "/snapshot.json", type(exc).__name__)
                if "data.json" in names and os.path.basename(directory) == "dist":
                    try:
                        published(host, directory, json.loads(reader(os.path.join(directory, "data.json"))()), "published")
                    except (OSError, ValueError) as exc:
                        error(directory + "/data.json", type(exc).__name__)
                for name in sorted(names):
                    if name.endswith((".tar", ".tar.gz", ".tgz")) and name not in SKIP_ARCHIVES:
                        archive(host, os.path.join(directory, name))


main(sys.argv[1], sys.argv[2:])
'''

SOURCE_RANK = {"status": 0, "trajectory": 1, "transport": 2, "proof": 3, "blocker": 4, "snapshot": 5, "published": 6}
# Path markers of copies (archive staging, export bundles, proof collections, repo snapshots, public builds).
COPY_MARKERS = re.compile(r"archive-recovery|keygen-export|collected-proofs|/repo[-/]|/repo\.tar|keygen-public|"
                          r"snapshots|keygen-web-|/dist|qualification-proofs|rescore|legacy/.*/web/")
# Synthetic fixtures built to test publication tooling; they reuse real usage numbers but are not attempts.
SYNTHETIC = re.compile(r"THROWAWAY|synthetic-not-real")
HOST_ORDER = {label: index for index, (label, _, _) in enumerate(HOSTS)}
ROUTE_PREFIX = re.compile(r"^(codex_oauth|anthropic_oauth|go|vercel|devin|nim)-")
# Legacy gateway route ids embed the vendor slug: vercel-<vendor>-<model>.
VENDOR_PREFIX = re.compile(r"^vercel-(alibaba|google|meta|minimax|mistral|moonshotai|zai|tencent|spacexai|xai|"
                           r"nvidia|openai|deepseek|cohere|inception|stepfun|arcee-ai|thinkingmachines)-")
SUFFIXES = re.compile(r"-(messages|responses|chat-final|chat)$")
# Legacy ids for the same checkpoint (keys and values are canonical ids, see canon()). Prices are keyed by
# canonical id too, which maps the legacy price ids in prices.json (claude-5-fable, gemini-3-1-pro, ...).
SAME_MODEL = {"claude-5-fable": "claude-fable-5", "gemini-3-1-pro": "gemini-3-1-pro-preview",
              "nemotron-3-ultra": "nemotron-3-ultra-550b-a55b", "muse-spark-1-2": "muse-spark-1-2-contributor",
              "muse-spark-1-3": "muse-spark-1-3-contributor"}
# Display names for canonical ids recorded only in dashed form.
DISPLAY = {"kimi-k2-7": "kimi-k2.7"}

RETRIEVED = "2026-10-02"


def rate(basis: str, url: str, inp: float, cached: float | None, out: float) -> dict:
    return {"input_usd_per_m": inp, "cached_input_usd_per_m": cached, "output_usd_per_m": out,
            "source_url": url, "retrieved": RETRIEVED, "basis": basis}


def free(url: str) -> dict:
    return rate("free", url, 0.0, 0.0, 0.0)


VERCEL = "https://vercel.com/ai-gateway/models.md"
NIM_FREE = "https://build.nvidia.com/"  # "Free inference with leading models"; the nim route is integrate.api.nvidia.com
DEVIN = "https://docs.devin.ai/desktop/models"
# Per-token list prices ($/1M) for models without a maker-published row in web/prototype/data-src/prices.json.
# basis "maker": the maker's own API price page; "route": no maker API price exists, so the price of the
# route the attempt used (go = OpenCode Go, vercel = Vercel AI Gateway, nim = NVIDIA build endpoints,
# devin = Devin); "free": that route serves the model at no per-token charge. Keys are canonical ids;
# "*" applies to every route not listed.
PRICE_SOURCES = {
    "hy3": {"*": rate("maker", "https://www.tencentcloud.com/document/product/1300/78937", 0.132, 0.033, 0.528)},
    "hy4-preview": {"*": rate("maker", "https://www.tencentcloud.com/document/product/1300/78937", 0.834, 0.042, 2.501)},
    "longcat-2-0": {"*": rate("maker", "https://longcat.chat/platform/docs/pricing/longcat-2.0", 0.30, 0.006, 1.20)},
    "command-a": {"*": rate("maker", "https://cohere.com/blog/command-a", 2.50, None, 10.00)},
    "mercury-2-5": {"*": rate("maker", "https://api.inceptionlabs.ai/v1/models", 0.04, 0.004, 0.15)},
    "gemini-3-flash": {"*": rate("maker", "https://ai.google.dev/gemini-api/docs/pricing", 0.50, 0.05, 3.00)},
    "step-3-7-flash": {"*": rate("maker", "https://platform.stepfun.ai/docs/en/guides/pricing/details", 0.20, 0.04, 1.15)},
    "step-5-preview": {"*": rate("maker", "https://platform.stepfun.ai/docs/en/guides/pricing/details", 1.00, 0.05, 2.70)},
    "trinity-large-thinking": {"*": rate("maker", "https://docs.arcee.ai/get-started/pricing", 0.25, 0.06, 0.80)},
    # Cognition publishes its SWE model prices on the Devin model page.
    "swe-1-6": {"*": rate("maker", DEVIN, 0.50, 0.20, 2.50)},
    "swe-1-7": {"*": rate("maker", DEVIN, 0.50, 0.20, 2.50)},
    "swe-1-7-lightning": {"*": rate("maker", DEVIN, 2.50, 1.00, 12.50)},
    "swe-2": {"*": rate("maker", DEVIN, 0.75, 0.075, 3.75)},
    # Moonshot lists only kimi-k2.7-code; plain kimi-k2.7 ran through Devin.
    "kimi-k2-7": {"*": rate("route", DEVIN, 0.95, 0.19, 4.00)},
    "space-bunny-free": {"*": free("https://opencode.ai/docs/go/")},
    # Google's Gemini API serves Gemma 4 on the free tier only (paid tier "Not available").
    "gemma-4-31b-it": {"*": rate("route", VERCEL, 0.14, 0.10, 0.40), "nim": free(NIM_FREE)},
    # OpenAI publishes no API price for the open-weights gpt-oss models.
    "gpt-oss-120b": {"*": rate("route", VERCEL, 0.35, 0.35, 0.75), "devin": rate("route", DEVIN, 0.15, 0.07, 0.60)},
    # Thinking Machines prices Inkling only on Tinker, its fine-tuning service, not as an inference API.
    "inkling": {"*": rate("route", VERCEL, 0.95, 0.16, 4.05), "devin": rate("route", DEVIN, 1.40, 0.26, 4.40)},
    # NVIDIA publishes no per-token price for its open Nemotron models.
    "nemotron-3-ultra-550b-a55b": {"*": rate("route", VERCEL, 0.50, 0.10, 2.20), "nim": free(NIM_FREE),
                                   "devin": rate("route", DEVIN, 0.60, 0.12, 2.40)},
    "nemotron-3-super-120b-a12b": {"*": rate("route", VERCEL, 0.15, None, 0.65), "nim": free(NIM_FREE)},
}


def route_of(record: dict) -> str | None:
    if record.get("provider"):
        return record["provider"]
    for text in (record.get("model") or "", Path(record["path"].split(":", 1)[0]).name):
        match = re.match(r"^(codex_oauth|anthropic_oauth|go|vercel|devin|nim)[-/]", text.lower())
        if match:
            return match.group(1)
    return None


def price_for(key: str, route: str | None, prices: dict) -> dict | None:
    """Maker price from prices.json, else the PRICE_SOURCES row for this route; None when none is known."""
    listed = public_price(prices.get(key, {}))
    if listed["input_usd_per_m"] is not None:
        return {**listed, "basis": "maker"}
    sources = PRICE_SOURCES.get(key) or {}
    return sources.get(route or "*") or sources.get("*")


def canon(model: str) -> str:
    key = model.lower().replace(".", "-")
    return SAME_MODEL.get(key, key)


def display_model(raw: str | None) -> str:
    name = re.sub(r"\s*\(.*\)$", "", (raw or "unknown").strip().lower())
    name = VENDOR_PREFIX.sub("", name)
    name = ROUTE_PREFIX.sub("", price_id(name)).rsplit("/", 1)[-1]
    return SUFFIXES.sub("", name)


def collect(label: str, target: str | None, roots: list[str]) -> tuple[list[dict], list[dict], str | None]:
    command = ["python3", "-", label, *roots]
    if target:
        command = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", target,
                   " ".join(shlex.quote(part) for part in command)]
    try:
        result = subprocess.run(command, input=COLLECTOR, capture_output=True, text=True, timeout=1800)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], [], f"{type(exc).__name__}"
    if result.returncode:
        return [], [], f"collector exit {result.returncode}: {result.stderr.strip().splitlines()[-1:]}"
    records, errors = [], []
    for line in result.stdout.splitlines():
        item = json.loads(line)
        (errors if "error" in item else records).append(item)
    return records, errors, None


def campaign_of(record: dict) -> str:
    outer, _, inner = record["rel"].partition(":")
    if record["source"] in {"snapshot", "published"}:
        return "public:" + "/".join(Path(outer).parts[-2:])
    rel = [p for p in Path(outer).parts if p not in {".", ""}]
    if inner:
        rel = rel[:-1] + [p for p in inner.split("/") if p and p != "."]
    if len(rel) <= 2:
        return rel[0] if rel else "?"
    return f"{rel[0]}/{rel[-2]}"


def main() -> None:
    prices = {canon(p["id"]): p for p in json.loads((ROOT / "web/prototype/data-src/prices.json").read_text())["models"]}
    records, unreadable, per_host = [], [], {}
    for label, target, roots in HOSTS:
        found, errors, failure = collect(label, target, roots)
        if failure:
            unreadable.append({"host": label, "source": "controller", "reason": failure})
        unreadable += [{"host": label, "source": e["error"], "reason": e["reason"]} for e in errors]
        for record in found:
            record["campaign"] = campaign_of(record)
            record["copy"] = bool(COPY_MARKERS.search(record["path"]))
        records += found
        per_host[label] = found

    synthetic = [r for r in records if SYNTHETIC.search(r["path"])]
    records = [r for r in records if not SYNTHETIC.search(r["path"])]
    usable = [r for r in records if r.get("tokens") and (r["tokens"]["prompt"] or r["tokens"]["completion"])]
    usable_ids = {id(r) for r in usable}
    no_usage = [r for r in records if not r.get("tokens")]
    groups: dict[tuple, list[dict]] = defaultdict(list)
    variants: dict[str, Counter] = defaultdict(Counter)
    for record in usable:
        record["model_key"] = canon(display_model(record["model"]))
        variants[record["model_key"]][display_model(record["model"])] += 1
        t = record["tokens"]
        groups[(record["model_key"], t["prompt"], t["cached"], t["completion"])].append(record)

    def display(key: str) -> str:
        names = variants[key]
        dotted = [n for n in names if "." in n and canon(n) == key]
        return DISPLAY.get(key) or max(dotted or names, key=lambda n: (names[n], n))

    def maker(key: str, members: list[dict]) -> str:
        if prices.get(key, {}).get("maker"):
            return prices[key]["maker"]
        guesses = [public_maker(price_id(r["model"] or ""), {}) for r in members]
        return next((g for g in guesses if g != "Other"), public_maker(display(key), {}))

    attempts = []
    for (key, *_), members in groups.items():
        members.sort(key=lambda r: (SOURCE_RANK[r["source"]], r["copy"], HOST_ORDER[r["host"]], r["path"]))
        best = members[0]
        published_costs = [r["cost_usd"] for r in members if isinstance(r.get("cost_usd"), (int, float))]
        totals = {"prompt_tokens": best["tokens"]["prompt"], "cached_tokens": best["tokens"]["cached"],
                  "completion_tokens": best["tokens"]["completion"]}
        route = next((r for r in map(route_of, members) if r), None)
        price = price_for(key, route, prices)
        usd = published_costs[0] if published_costs else (estimate_cost(totals, price) if price else None)
        attempts.append({"key": key, "name": display(key), "maker": maker(key, members), "usd": usd, "best": best,
                         "copies": len(members), "tokens": best["tokens"], "route": route,
                         "basis": "maker" if published_costs else (price or {}).get("basis") if usd is not None else None,
                         "source_url": (price or {}).get("source_url")})

    models: dict[str, dict] = {}
    bases: dict[str, Counter] = defaultdict(Counter)
    for a in attempts:
        m = models.setdefault(a["name"], {"name": a["name"], "maker": a["maker"], "runs": 0, "usd": None,
                                          "unpriced_runs": 0, "price_basis": None})
        m["runs"] += 1
        if a["usd"] is None:
            m["unpriced_runs"] += 1
        else:
            m["usd"] = round((m["usd"] or 0) + a["usd"], 4)
            bases[a["name"]][a["basis"]] += 1
    for name, counts in bases.items():
        paid = Counter({basis: n for basis, n in counts.items() if basis != "free"})
        models[name]["price_basis"] = paid.most_common(1)[0][0] if paid else "free"
    priced = [a for a in attempts if a["usd"] is not None]
    unpriced = [a for a in attempts if a["usd"] is None]
    spend = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "basis": ("Every recorded attempt's input, cached-input and output tokens (reasoning billed as output) times "
                  "the maker's published per-token list price, or, where the maker publishes none, the list price of "
                  "the route the attempt used (free routes at $0); not an actual provider bill."),
        "total_usd": round(sum(a["usd"] for a in priced), 2),
        "runs": len(attempts),
        "priced_runs": len(priced),
        "unpriced_runs": len(unpriced),
        "unpriced_tokens": {"input": sum(a["tokens"]["prompt"] for a in unpriced),
                            "output": sum(a["tokens"]["completion"] for a in unpriced)},
        "models": sorted(models.values(), key=lambda m: (m["usd"] is None, -(m["usd"] or 0), -m["runs"], m["name"])),
    }
    text = json.dumps(spend, indent=1, ensure_ascii=True) + "\n"
    for output in OUTPUTS:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text)

    print(f"records read: {len(records)} (with token usage {len(usable)}, without usage {len(no_usage)})")
    print(f"synthetic publication fixtures excluded: {len(synthetic)} records")
    print(f"unique attempts: {len(attempts)}; duplicate copies merged: {len(usable) - len(attempts)}")
    for label, found in per_host.items():
        kept = [a for a in attempts if a["best"]["host"] == label]
        print(f"  {label}: {len(found)} records, {sum(1 for r in found if id(r) in usable_ids)} with usage, "
              f"{len(kept)} unique attempts attributed, ${sum(a['usd'] or 0 for a in kept):.2f}")
    print("per campaign (host, campaign: attempts, usd, unpriced):")
    campaigns: dict[tuple, list] = defaultdict(lambda: [0, 0.0, 0])
    for a in attempts:
        c = campaigns[(a["best"]["host"], a["best"]["campaign"])]
        c[0] += 1
        c[1] += a["usd"] or 0
        c[2] += a["usd"] is None
    for (host, campaign), (count, usd, missing) in sorted(campaigns.items()):
        print(f"  {host:8} {campaign}: {count}, ${usd:.2f}, {missing}")
    print(f"total ${spend['total_usd']:.2f} over {spend['runs']} attempts ({spend['priced_runs']} priced, "
          f"{spend['unpriced_runs']} unpriced; unpriced tokens in {spend['unpriced_tokens']['input']:,} "
          f"out {spend['unpriced_tokens']['output']:,})")
    print("priced from PRICE_SOURCES (model, route, basis, attempts, usd, source):")
    sourced: dict[tuple, list] = defaultdict(lambda: [0, 0.0])
    for a in attempts:
        if a["key"] in PRICE_SOURCES and a["usd"] is not None:
            row = sourced[(a["name"], a["route"], a["basis"], a["source_url"])]
            row[0] += 1
            row[1] += a["usd"]
    for (name, route, basis, url), (count, usd) in sorted(sourced.items(), key=lambda item: -item[1][1]):
        print(f"  {name} [{route}] {basis}: {count}, ${usd:.2f}, {url}")
    print("top unpriced models:")
    for m in sorted((m for m in models.values() if m["unpriced_runs"]), key=lambda m: -m["unpriced_runs"])[:10]:
        tokens = [a["tokens"] for a in unpriced if a["name"] == m["name"]]
        print(f"  {m['name']} ({m['maker']}): {m['unpriced_runs']} attempts, "
              f"in {sum(t['prompt'] for t in tokens):,} out {sum(t['completion'] for t in tokens):,}")
    print(f"attempt records without usage evidence (not counted): {len(no_usage)}")
    print(f"unreadable sources: {len(unreadable)}")
    for item in unreadable[:40]:
        print(f"  {item['host']}: {item['source']} ({item['reason']})")
    for output in OUTPUTS:
        print(f"wrote {output}")


if __name__ == "__main__":
    main()
