"""PROTOTYPE data export for the FT2-styled results site. Throwaway; see web/prototype/README.md.

Reads the scored report embedded in benchmark/runs/index.html plus each run directory, and writes
web/prototype/dist/{data.json, media/<slug>.{xm,mp3}} for the static front-end.

    python web/prototype/build.py            # data + media (mp3 transcode is cached)
    python web/prototype/build.py --serve    # same, then serve on 0.0.0.0:8780
"""
import gzip
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "benchmark/runs"
HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
MEDIA = DIST / "media"

FLAG_RULES = {
    "PHRASE_SAMPLE": "A used sample plays over 8 s at its root note, or over 25% of the song.",
    "SAMPLE_HEAVY": "Used sample seconds at root notes exceed 50% of the song length.",
    "ONE_INSTRUMENT": "Only one instrument is ever triggered.",
    "SPARSE": "Fewer than 64 note-ons, or fewer than 2 channels ever triggered.",
    "SILENCE": "Over 20% of 100 ms blocks below -60 dBFS, or a silent run over 4 s.",
    "TAIL_SILENCE": "Over 1 s of silence before the end of the render.",
    "CLIPPING": "Over 0.1% of samples at full scale.",
    "QUIET": "Integrated loudness below -30 LUFS.",
    "FLAT": "95th-to-10th percentile block RMS range under 2 dB.",
    "SEAM": "Worst measured FT2 loop transition below 50%, or no restart observed.",
    "MASKED": "Lead melody masked in over 35% of its bands (diagnostic only).",
    "SUSTAINED_NOISE": "Sustained-noise integrity below 0.8.",
    "RAW_XM": "tune.xm was written without module_save (allowed; recorded).",
}

# Access routes (proxies, subscriptions, relays) are private: nothing below may reach data.json.
PROVIDER_PREFIX = r"^(devin/|go-|vercel-[a-z]+/)"
PUBLIC_PRICE_HOSTS = (  # maker-published pricing pages only; third-party/proxy tables are not shown
    "developers.openai.com", "openai.com", "platform.claude.com", "ai.google.dev", "docs.x.ai", "api-docs.deepseek.com",
    "docs.z.ai", "platform.kimi.ai", "alibabacloud.com", "mimo.mi.com", "platform.minimax.io",
    "dev.meta.ai", "docs.mistral.ai",
)


def price_id(model: str) -> str:
    m = re.sub(r"\s*\(.*\)$", "", model)
    return re.sub(PROVIDER_PREFIX, "", m)


def public_price(price: dict) -> dict:
    """Maker list price, or all-null when the only source is a proxy/aggregator."""
    keys = ("input_usd_per_m", "cached_input_usd_per_m", "output_usd_per_m")
    url = price.get("source_url") or ""
    if not any(host in url for host in PUBLIC_PRICE_HOSTS):
        return {**{k: None for k in keys}, "source_url": None}
    return {**{k: price[k] for k in keys}, "source_url": url}


def public_error(err: str) -> str:
    return "" if re.search(r"proxy|relay|driver|web ui|acct", err or "", re.I) else (err or "")


def slug(model: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", price_id(model).lower()).strip("-") + ("-exh" if "exhibition" in model else "")


def estimate_cost(totals: dict, price: dict) -> float | None:
    if not totals or price.get("input_usd_per_m") is None:
        return None
    cached = totals.get("cached_tokens") or 0
    fresh = max(0, (totals.get("prompt_tokens") or 0) - cached)
    cached_rate = price["cached_input_usd_per_m"]
    if cached_rate is None:
        cached_rate = price["input_usd_per_m"]
    return round((fresh * price["input_usd_per_m"] + cached * cached_rate
                  + (totals.get("completion_tokens") or 0) * price["output_usd_per_m"]) / 1e6, 4)


def compact_trace(path: Path, max_frame: int) -> list[list[int]]:
    """[frame, order, row, pattern] for every executed row up to the canonical render's end."""
    out = []
    with gzip.open(path, "rt") as fh:
        for line in fh:
            ev = json.loads(line)
            if ev.get("kind") != "row":
                continue
            if ev["frame"] > max_frame:
                break
            out.append([ev["frame"], ev["order"], ev["row"], ev["pattern"]])
    return out


def worst_transition(loop: dict) -> dict | None:
    ts = [t for t in loop.get("transitions") or [] if isinstance(t.get("quality_score"), (int, float))]
    if not ts:
        return None
    t = min(ts, key=lambda t: t["quality_score"])
    return {k: t.get(k) for k in ("seconds", "kind", "from_order", "from_row", "to_order", "to_row", "quality_score", "components")}


# Public display names where the run id differs from the product name.
DISPLAY_NAMES = {}
# Exhibition runs went through a chat web UI: no API token counts exist. Wall time, turns and shell commands
# are recovered from their session logs instead; token/cost fields stay null (not billed per token).
EXHIBITION_LOGS = {"gpt-6-pro": "gpt6pro-exhibition", "claude-3-opus-20240229": "opus3-exhibition"}


def exhibition_usage(name: str) -> dict | None:
    d = EXHIBITION_LOGS.get(name)
    if not d or not (RUNS / d / "driver-log.jsonl").exists():
        return None
    events = [json.loads(line) for line in (RUNS / d / "driver-log.jsonl").read_text().splitlines() if line.strip()]
    relay = RUNS / d / "relay-log.jsonl"
    commands = sum(1 for line in relay.read_text().splitlines() if line.strip()) if relay.exists() else None
    ats = [e["at"] for e in events if "at" in e]
    return {"turns": sum(1 for e in events if e.get("event") == "reply"), "commands": commands,
            "wall_minutes": round((max(ats) - min(ats)) / 60, 1) if ats else None}


def main() -> None:
    html = (RUNS / "index.html").read_text(encoding="utf-8")
    report = json.loads(re.search(r"const DATA=(\[.*?\]);\n", html, re.S).group(1))
    prices = {p["id"]: p for p in json.loads((HERE / "data-src/prices.json").read_text())["models"]}
    MEDIA.mkdir(parents=True, exist_ok=True)
    runs = []
    for d in report:
        run_dir = RUNS / d["run_dir"]
        status = json.loads((run_dir / "status.json").read_text())
        profile = json.loads((run_dir / "profile.json").read_text()) if (run_dir / "profile.json").exists() else {}
        price = prices[price_id(d["model"])]
        s = slug(d["model"])
        media = {}
        xm = run_dir / "submission/tune.xm"
        if d["files"].get("xm") and (RUNS / d["files"]["xm"]).exists():
            xm = RUNS / d["files"]["xm"]
        if xm.exists():
            shutil.copyfile(xm, MEDIA / f"{s}.xm")
            media["xm"] = f"media/{s}.xm"
        wav = run_dir / "canonical/canonical.wav"
        if wav.exists():
            mp3 = MEDIA / f"{s}.mp3"
            if not mp3.exists() or mp3.stat().st_mtime < wav.stat().st_mtime:
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-codec:a", "libmp3lame", "-b:a", "160k", str(mp3)], check=True)
            media["audio"] = f"media/{s}.mp3"
        audio = status.get("audio") or {}
        trace = []
        if (run_dir / "playback/trace.jsonl.gz").exists() and audio.get("duration_seconds"):
            trace = compact_trace(run_dir / "playback/trace.jsonl.gz", int(audio["duration_seconds"] * 44100))
        totals = status.get("totals") or {}
        structure = profile.get("structure") or {}
        pub_price = public_price(price)
        runs.append({
            "slug": s,
            "name": DISPLAY_NAMES.get(price_id(d["model"]), price_id(d["model"])),
            "maker": price["maker"],
            "exhibition": "(exhibition)" in d["model"],
            "tier": d["tier"],
            "status": d["status"],
            "error": public_error(d["error"]),
            "score": d["craft"],
            "parts": {k: (d["parts"] or {}).get(k, 0.0) for k in ("tonal_organization", "development", "dynamics")},
            "weights": d["weights"],
            "factors": {k: (d["factors"] or {}).get(k, 0.0) for k in ("signal_integrity", "noise_integrity", "loop_continuity", "duration_sufficiency")},
            "uncapped": d["uncapped"],
            "content": d["content_score"],
            "caps": d["caps"],
            "flags": [{"id": f, "rule": FLAG_RULES.get(f, "")} for f in d["flags"]],
            "loop": {"quality": (d["loop"] or {}).get("quality_score"), "worst": worst_transition(d["loop"] or {})},
            "tonal": {k: (d["spectral"] or {}).get(k) for k in ("tonal_evidence_fraction", "diatonic_concentration", "effective_pitch_classes", "sustained_noise_fraction")},
            "development": {k: structure.get(k) for k in ("arrangement_score", "sequence_coverage", "motif_recurrence", "controlled_development")},
            "audio": {"duration": audio.get("duration_seconds"), "lufs": d["lufs"], "peak": audio.get("peak")},
            "module": {**(status.get("module") or {}), "patterns": d["patterns"], "instruments": d["instr"], "samples": d["samples"]},
            "usage": {
                "requests": totals.get("requests"), "prompt_tokens": totals.get("prompt_tokens"),
                "cached_tokens": totals.get("cached_tokens"), "completion_tokens": totals.get("completion_tokens"),
                "reasoning_tokens": totals.get("reasoning_tokens"), "commands": totals.get("commands"),
                "wall_minutes": round((status.get("wall_seconds") or 0) / 60, 1), "attempts": d["attempts"],
                "turns": None,
                **({k: v for k, v in (exhibition_usage(price_id(d["model"])) or {}).items()} if "(exhibition)" in d["model"] else {}),
            },
            "price": pub_price,
            "cost_usd": estimate_cost(totals, pub_price),
            "media": media,
            "trace": trace,
        })
    runs.sort(key=lambda r: (r["exhibition"], r["status"] != "RENDERED_UNSCORED", -r["score"]))
    rank = 0
    for r in runs:
        r["failed"] = r["status"] != "RENDERED_UNSCORED"
        r["rank"] = None if r["exhibition"] or r["failed"] else (rank := rank + 1)
    out = {
        "generated": "2026-09-29",
        "formula": {
            "content": "50 x tonal organization + 40 x development + 10 x dynamics",
            "score": "content x signal integrity x noise integrity x (0.75 + 0.25 x loop quality) x duration sufficiency, then caps; rounded to 0.1",
            "duration": "min(1, first-pass audible seconds / 30)",
        },
        "flag_rules": FLAG_RULES,
        "runs": runs,
    }
    (DIST / "data.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"{len(runs)} runs -> {DIST / 'data.json'} ({(DIST / 'data.json').stat().st_size // 1024} KB)")


if __name__ == "__main__":
    import sys

    main()
    if "--serve" in sys.argv:
        import functools
        import http.server

        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(HERE))
        print("serving on 0.0.0.0:8780 -> http://<host>:8780/?variant=A")
        http.server.ThreadingHTTPServer(("0.0.0.0", 8780), handler).serve_forever()
