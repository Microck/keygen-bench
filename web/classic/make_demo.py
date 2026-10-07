#!/usr/bin/env python3
"""Make a branded, shareable video of one benchmark run: the site's Tracker playing the tune.

The video shows the real results site (FT2 Tracker with moving pattern editor and scopes) above a branded
footer (model, score, rank, cost, URL), with a title card before, an end card after, and the run's own MP3
as the soundtrack.
Output is written to a private folder and is never part of the repository.

  python web/classic/make_demo.py --model qwen3.5-397b-a17b
  python web/classic/make_demo.py --model hermes-4-405b --attempt 2 --aspect 4:3,1:1 --clip catchy

--site defaults to the public site. For a run that is not published, build and serve a local publication
(see README) and pass its URL. Requires Playwright with Chromium, ffmpeg and numpy.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import html
import json
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import numpy as np
import re

# Output size and page layout size (CSS px) per aspect. The page is captured at exactly 2x, so every FT2 font
# pixel is a 2x2 block with no resampling; 1:1 is 600 px wide because narrower windows switch the site to its
# phone layout.
ASPECTS = {"4:3": ((1440, 1080), (720, 540)), "1:1": ((1200, 1200), (600, 600))}
FOOTER = 46                      # branded bar under the site, CSS px
CARD_SECONDS = 2.0               # title and end card
MAX_SECONDS = 140.0              # X/Twitter video limit
FPS = 30
PUBLIC_URL = "https://keygen.micr.dev"


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def pick_run(data: dict, model: str, attempt: int | None) -> dict:
    runs = [r for r in data["runs"] if r.get("model_key") == model]
    for r in runs:
        # data.json carries the ordinal in the name: "model (max-tier, attempt 2)".
        found = re.search(r"attempt (\d+)\)", r.get("name", ""))
        r["attempt"] = r.get("attempt") or (int(found.group(1)) if found else 1)
    if not runs:
        raise SystemExit(f"No scored run for model {model!r} on this site")
    if attempt is not None:
        match = [r for r in runs if r.get("attempt") == attempt]
        if not match:
            raise SystemExit(f"{model} has no scored attempt {attempt}; scored: {sorted(r.get('attempt') for r in runs)}")
        return match[0]
    return max(runs, key=lambda r: r.get("score") or 0)


def media_url(site: str, path: str) -> str:
    return path if path.startswith(("http://", "https://")) else f"{site}/dist/{path}"


def catchiest_start(mp3: Path, seconds: float) -> float:
    """Start of the window with the highest combined loudness and note activity (RMS plus positive RMS change)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp3), "-ac", "1", "-ar", "11025", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    hop = 1103  # 0.1 s
    frames = len(x) // hop
    if frames * 0.1 <= seconds:
        return 0.0
    rms = np.sqrt(np.mean(x[: frames * hop].reshape(frames, hop) ** 2, axis=1) + 1e-12)
    activity = np.maximum(np.diff(rms, prepend=rms[0]), 0)

    def norm(v):
        return v / (v.max() or 1)
    score = 0.6 * norm(rms) + 0.4 * norm(activity)
    width = int(seconds * 10)
    sums = np.convolve(score, np.ones(width), "valid")
    return round(float(np.argmax(sums[::10]) * 1.0), 1)  # whole seconds


CARD_CSS = """
html, body { margin: 0; background: #000; }
.card { width: %dpx; height: %dpx; box-sizing: border-box; background: var(--desktop); color: #fff;
        font: 10px/11px "FT2", monospace; -webkit-font-smoothing: none; display: flex; flex-direction: column; }
.bevel { border: 1px solid; border-color: var(--dsktop1) var(--dsktop2) var(--dsktop2) var(--dsktop1); }
.well { background: #000; border: 1px solid; border-color: var(--dsktop2) var(--dsktop1) var(--dsktop1) var(--dsktop2); }
.big { font: 20px/20px "FT2 Big", monospace; text-shadow: 1px 1px 0 var(--dsktop2); }
.dim { color: var(--dim); } .blue { color: var(--pattext); }
"""


def bar_html(w: int, h: int, run: dict, total: int) -> str:
    """The site's own top bar already says KEYGEN BENCH; the footer adds the run, the score and the URL."""
    cost = f"${run['cost_usd']:.2f}" if run.get("cost_usd") else "$0" if run.get("cost_usd") == 0 else "n/a"
    body = f"""<div class="card bevel" style="padding:5px 8px;gap:4px">
      <div style="display:flex;justify-content:space-between;align-items:baseline">
        <span class="big">{html.escape(run['model_key'])} <span style="color:#fff">{run['score']:.1f}</span></span><span class="big blue">keygen.micr.dev</span></div>
      <div class="dim">{html.escape(run['maker'])} | attempt {run['attempt']} | rank {run.get('rank', '-')} of {total} | cost {cost}</div>
      </div>"""
    return f"<div style='width:{w}px;height:{h}px'>{body}</div>"


def card_html(kind: str, w: int, h: int, run: dict, total: int) -> str:
    if kind == "title":
        lines = f"""<div class="big" style="font-size:40px;line-height:40px">KEYGEN BENCH</div>
          <div class="blue" style="font-size:20px;line-height:22px">Can an AI write keygen music?</div>
          <div class="well" style="padding:10px 14px;margin-top:10px"><div class="big">{html.escape(run['model_key'])}</div>
          <div class="dim" style="margin-top:4px">{html.escape(run['maker'])}</div></div>"""
    else:
        lines = f"""<div class="big" style="font-size:40px;line-height:40px">{run['score']:.1f}</div>
          <div class="dim">{html.escape(run['model_key'])} | rank {run.get('rank', '-')} of {total}</div>
          <div class="well" style="padding:10px 14px;margin-top:10px;text-align:center">
          <div class="dim">Every model, 3 attempts, scored in FastTracker II</div>
          <div class="big blue" style="margin-top:6px">keygen.micr.dev</div></div>"""
    return f'<div class="card bevel" style="align-items:center;justify-content:center;gap:8px;text-align:center">{lines}</div>'


async def render_png(page, site: str, markup: str, w: int, h: int, out: Path) -> None:
    await page.set_viewport_size({"width": w, "height": h})
    await page.set_content(f"""<html><head><link rel="stylesheet" href="{site}/core/ft2.css">
      <style>{CARD_CSS % (w, h)}</style></head><body>{markup}</body></html>""")
    await page.evaluate("document.fonts.ready")
    await page.wait_for_timeout(200)
    await page.screenshot(path=str(out))


async def record(args, site: str, run: dict, total: int, aspect: str, start: float, seconds: float, work: Path) -> Path:
    from playwright.async_api import async_playwright
    (out_w, out_h), (w, h) = ASPECTS[aspect]
    app_h = h - FOOTER
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=args.chrome, args=["--autoplay-policy=no-user-gesture-required"])
        context = await browser.new_context(viewport={"width": w, "height": app_h}, device_scale_factor=2)
        page = await context.new_page()
        # Branded stills come from the site's own stylesheet and FT2 fonts (same origin as the site).
        await page.goto(f"{site}/robots.txt")
        await render_png(page, site, bar_html(w, FOOTER, run, total), w, FOOTER, work / "footer.png")
        await render_png(page, site, card_html("title", w, h, run, total), w, h, work / "title.png")
        await render_png(page, site, card_html("end", w, h, run, total), w, h, work / "end.png")
        await page.set_viewport_size({"width": w, "height": app_h})
        await page.goto(f"{site}/tracker/{run['model_key']}/{run['attempt']}", wait_until="domcontentloaded")
        await page.wait_for_function("document.querySelector('.transport .lcd') && document.querySelector('.seek')", timeout=60000)
        await page.wait_for_timeout(4000)  # preloader, fonts and module download
        frames: list[tuple[float, Path]] = []
        cdp = await context.new_cdp_session(page)

        async def on_frame(event):
            path = work / f"f{len(frames):06d}.png"
            path.write_bytes(base64.b64decode(event["data"]))
            frames.append((event["metadata"]["timestamp"], path))
            try:
                await cdp.send("Page.screencastFrameAck", {"sessionId": event["sessionId"]})
            except Exception:  # frames still in flight when the browser closes
                pass

        cdp.on("Page.screencastFrame", lambda e: asyncio.ensure_future(on_frame(e)))
        if start > 0:
            box = await page.locator(".seek").bounding_box()
            duration = run["audio"]["duration"]
            await page.mouse.click(box["x"] + box["width"] * start / duration, box["y"] + box["height"] / 2)
            await page.wait_for_timeout(500)
        await cdp.send("Page.startScreencast", {"format": "png", "maxWidth": w * 2, "maxHeight": app_h * 2})
        lcd = page.locator(".transport .lcd").first
        before = await lcd.inner_text()
        await page.get_by_role("button", name="Play", exact=True).click()
        # The time display ticks to the next whole second exactly when the audio clock crosses it; that
        # moment, minus the fraction of a second still to go when playback began, is the audio start.
        while (await lcd.inner_text()) == before:
            await asyncio.sleep(0.005)
        tick = time.time()
        audio_start = tick - ((int(start) + 1) - start)
        await asyncio.sleep(max(0.0, audio_start + seconds - time.time()) + 0.3)
        await cdp.send("Page.stopScreencast")
        await browser.close()
    # Frames → constant-rate video spanning exactly [audio_start, audio_start + seconds].
    listing = work / "frames.txt"
    rows = [(t, p) for t, p in frames if t <= audio_start + seconds]
    first = max([i for i, (t, _) in enumerate(rows) if t <= audio_start] or [0])
    rows = rows[first:]
    with listing.open("w") as f:
        for i, (t, path) in enumerate(rows):
            nxt = rows[i + 1][0] if i + 1 < len(rows) else audio_start + seconds
            dur = nxt - max(t, audio_start)
            f.write(f"file '{path.name}'\nduration {max(dur, 0.001):.4f}\n")
        f.write(f"file '{rows[-1][1].name}'\n")
    app = work / "app.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-vf",
                    f"fps={FPS},scale={out_w}:{round(out_h * app_h / h / 2) * 2}:flags=lanczos", "-c:v", "libx264", "-qp", "0",
                    "-pix_fmt", "yuv444p", str(app)], check=True, cwd=work)
    return app


def compose(app: Path, work: Path, mp3: Path, aspect: str, start: float, seconds: float, out: Path) -> None:
    (out_w, out_h), (_, h) = ASPECTS[aspect]
    foot = out_h - round(out_h * (h - FOOTER) / h / 2) * 2
    c = CARD_SECONDS
    fade = min(1.5, seconds / 4)
    filtergraph = (
        f"[1:v]scale={out_w}:{foot}:flags=lanczos[ft];"
        f"[0:v][ft]vstack=inputs=2,fps={FPS},setsar=1[main];"
        f"[2:v]scale={out_w}:{out_h},fps={FPS},setsar=1,format=yuv420p[ti];"
        f"[3:v]scale={out_w}:{out_h},fps={FPS},setsar=1,format=yuv420p[en];"
        f"[main]format=yuv420p[mn];[ti][mn][en]concat=n=3:v=1:a=0[v];"
        f"[4:a]atrim=start={start}:duration={seconds},asetpts=PTS-STARTPTS,afade=t=in:d=0.05,"
        f"afade=t=out:st={seconds - fade}:d={fade},adelay={int(c * 1000)}:all=1,apad=whole_dur={seconds + 2 * c}[a]"
    )
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(app),
                    "-loop", "1", "-t", str(seconds), "-i", str(work / "footer.png"),
                    "-loop", "1", "-t", str(c), "-i", str(work / "title.png"),
                    "-loop", "1", "-t", str(c), "-i", str(work / "end.png"),
                    "-i", str(mp3), "-filter_complex", filtergraph, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "10", "-preset", "slow", "-tune", "animation", "-pix_fmt", "yuv420p",
                    "-b:v", "0", "-maxrate", "25M", "-bufsize", "50M",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", str(seconds + 2 * c), str(out)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", required=True, help="Model key as in the site URL, e.g. qwen3.5-397b-a17b")
    parser.add_argument("--attempt", type=int, help="Attempt number (default: the model's best)")
    parser.add_argument("--aspect", default="4:3", help="4:3, 1:1, or both comma-separated (default 4:3)")
    parser.add_argument("--clip", choices=["full", "catchy"], default="full",
                        help="full: the whole loop (up to the 2:20 post limit); catchy: the liveliest window")
    parser.add_argument("--seconds", type=float, default=40, help="Length of the catchy clip (default 40)")
    parser.add_argument("--site", default=PUBLIC_URL, help="Results site URL (default: the public site)")
    parser.add_argument("--out", type=Path, default=Path.home() / "keygen-demos", help="Output folder (default ~/keygen-demos)")
    parser.add_argument("--chrome", help="Chromium executable (default: Playwright's)")
    args = parser.parse_args()
    aspects = [a.strip() for a in args.aspect.split(",")]
    if any(a not in ASPECTS for a in aspects):
        raise SystemExit(f"--aspect must be one or more of {', '.join(ASPECTS)}")
    site = args.site.rstrip("/")
    data = fetch_json(f"{site}/dist/data.json")
    run = pick_run(data, args.model, args.attempt)
    total = data.get("ranked_results") or len({r["model_key"] for r in data["runs"]})
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="keygen-demo-") as temporary:
        work = Path(temporary)
        mp3 = work / "tune.mp3"
        with urllib.request.urlopen(media_url(site, run["media"]["audio"]), timeout=120) as response:
            mp3.write_bytes(response.read())
        length = float(run["audio"]["duration"])
        budget = MAX_SECONDS - 2 * CARD_SECONDS
        if args.clip == "full":
            start, seconds = 0.0, min(length, budget)
        else:
            seconds = min(args.seconds, length, budget)
            start = catchiest_start(mp3, seconds)
        for aspect in aspects:
            frames = work / aspect.replace(":", "x")
            frames.mkdir()
            app = asyncio.run(record(args, site, run, total, aspect, start, seconds, frames))
            name = f"{run['model_key']}-a{run['attempt']}-{args.clip}-{aspect.replace(':', 'x')}.mp4"
            compose(app, frames, mp3, aspect, start, seconds, args.out / name)
            shutil.rmtree(frames)
            print(f"{args.out / name}  ({seconds + 2 * CARD_SECONDS:.0f} s, starts at {start:.0f} s of the tune)")
    url = f"{PUBLIC_URL}/tracker/{run['model_key']}/{run['attempt']}"
    tweet = (f"{run['model_key']} ({run['maker']}) composed this keygen tune in FastTracker II, offline, with one bash tool.\n"
             f"Score {run['score']:.1f}, rank {run.get('rank', '-')} of {total} on Keygen Bench.\n{url}")
    tweet_path = args.out / f"{run['model_key']}-a{run['attempt']}-tweet.txt"
    tweet_path.write_text(tweet + "\n")
    print(tweet_path)


if __name__ == "__main__":
    main()
