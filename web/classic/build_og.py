"""Build Open Graph preview images and per-route meta for the classic site.

    python3 web/classic/build_og.py --dist /absolute/publication/dist

Writes <dist>/og/home.png, <dist>/og/<model>.png and <dist>/og/meta.json. serve.py reads meta.json and
puts the matching og:/twitter: tags into index.html for each route, so link previews change with the
rankings and the model being linked. Rerun after every new data.json.
"""
import argparse
import json
from io import BytesIO
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
W, H, K = 1200, 630, 3  # 400x210 FT2 pixels at 3x
PAL = {"desktop": "#4D619A", "dsktop1": "#82A6FF", "dsktop2": "#20283D", "pattext": "#92BEFF", "dim": "#C3CEEA",
       "black": "#000000", "white": "#FFFFFF", "looppin": "#325E9F"}
SITE = "AI models writing keygen tunes in FastTracker II"


def font(n, px):
    with TTFont(HERE / "core" / "fonts" / f"ft2-font{n}.woff2") as source:
        source.flavor = None
        stream = BytesIO()
        source.save(stream)
    stream.seek(0)
    return ImageFont.truetype(stream, px)


SMALL, BIG, HUGE = font(1, 10 * K), font(2, 20 * K), font(2, 40 * K)


def score_color(s):
    return "#55FF55" if s >= 70 else "#FFFF55" if s >= 50 else "#FFAA00" if s >= 25 else "#FF5555"


def load_logos():
    src = (HERE / "core" / "logos.js").read_text()
    out = {}
    for m in re.finditer(r'"([^"]+)":\s*\{\s*tile:\s*(null|"#\w+"),\s*pal:\s*\{([^}]*)\},\s*px:\s*\[(.*?)\]', src, re.S):
        pal = dict(re.findall(r'(\w):\s*"(#\w+)"', m.group(3)))
        out[m.group(1)] = (None if m.group(2) == "null" else m.group(2).strip('"'), pal, re.findall(r'"([^"]+)"', m.group(4)))
    return out


LOGOS = load_logos()


def logo(img, maker, x, y, scale):
    L = LOGOS.get(maker)
    if not L:
        return
    tile, pal, px = L
    d = ImageDraw.Draw(img)
    if tile:
        d.rectangle([x, y, x + 16 * scale - 1, y + 16 * scale - 1], fill=tile)
    for yy, row in enumerate(px):
        for xx, ch in enumerate(row):
            if ch != ".":
                d.rectangle([x + xx * scale, y + yy * scale, x + (xx + 1) * scale - 1, y + (yy + 1) * scale - 1], fill=pal[ch])


def raised(d, box):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=PAL["desktop"])
    d.rectangle([x0, y0, x1, y0 + K - 1], fill=PAL["dsktop1"]); d.rectangle([x0, y0, x0 + K - 1, y1], fill=PAL["dsktop1"])
    d.rectangle([x0, y1 - K + 1, x1, y1], fill=PAL["dsktop2"]); d.rectangle([x1 - K + 1, y0, x1, y1], fill=PAL["dsktop2"])


def sunken(d, box):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=PAL["black"])
    d.rectangle([x0, y0, x1, y0 + K - 1], fill=PAL["dsktop2"]); d.rectangle([x0, y0, x0 + K - 1, y1], fill=PAL["dsktop2"])
    d.rectangle([x0, y1 - K + 1, x1, y1], fill=PAL["dsktop1"]); d.rectangle([x1 - K + 1, y0, x1, y1], fill=PAL["dsktop1"])


def text(d, xy, s, f, fill, shadow=None, anchor="la"):
    if shadow:
        d.text((xy[0] + K, xy[1] + K), s, font=f, fill=shadow, anchor=anchor)
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def canvas():
    img = Image.new("RGB", (W, H), PAL["desktop"])
    d = ImageDraw.Draw(img)
    d.fontmode = "1"  # bitmap fonts: no antialiasing
    raised(d, [0, 0, W - 1, 30 * K])
    text(d, (6 * K, 5 * K), "KEYGEN BENCH", BIG, PAL["white"], PAL["dsktop2"])
    return img, d


def base_name(name):
    # "glm-5-3 (max-tier, attempt 2)" / "glm-5-3 (attempt 2)" / "glm-5-3 (max-tier)" -> "glm-5-3"
    return re.sub(r"\s*\((?:[^()]*,\s*)?attempt\s+\d+\)\s*$|\s*\(max-tier\)\s*$", "", name, flags=re.I)


def models(data):
    by = {}
    for r in data["runs"]:
        by.setdefault(r.get("model_key") or r["slug"], []).append(r)
    out = []
    for key, runs in by.items():
        ok = sorted((r for r in runs if not r.get("failed")), key=lambda r: r["provenance"].get("attempt_ordinal", 1))
        if not ok:
            continue
        best = max(ok, key=lambda r: r["score"])
        out.append({"key": key, "label": base_name(best["name"]), "maker": best["maker"], "best": best,
                    "scores": [r["score"] for r in ok], "exhibition": best.get("exhibition")})
    ranked = sorted((m for m in out if not m["exhibition"]), key=lambda m: -m["best"]["score"])
    for i, m in enumerate(ranked):
        m["rank"] = i + 1
    return ranked


def home(ms, path, date):
    img, d = canvas()
    raised(d, [K, 32 * K, W - K - 1, H - K - 1])
    text(d, (6 * K, 37 * K), f"TOP 5 OF {len(ms)}", SMALL, PAL["white"], PAL["dsktop2"])
    text(d, (W - 6 * K, 37 * K), f"snapshot {date}", SMALL, PAL["dim"], anchor="ra")
    text(d, (W - 6 * K, 12 * K), SITE, font(1, 20), PAL["dim"], anchor="ra")
    sunken(d, [5 * K, 50 * K, W - 5 * K - 1, H - 6 * K - 1])
    row = 29 * K
    for i, m in enumerate(ms[:5]):
        y = 54 * K + i * row
        s = m["best"]["score"]
        text(d, (12 * K, y + 4 * K), str(m["rank"]), BIG, PAL["white"])
        logo(img, m["maker"], 34 * K, y + 5 * K, 4)
        text(d, (62 * K, y + 7 * K), m["label"], SMALL if len(m["label"]) > 22 else font(1, 13 * K), PAL["pattext"])
        bar_x, bar_w = 250 * K, 100 * K
        d.rectangle([bar_x, y + 9 * K, bar_x + round(bar_w * s / 100), y + 15 * K], fill=score_color(s))
        text(d, (W - 12 * K, y + 4 * K), f"{s:.1f}", BIG, PAL["white"], anchor="ra")
    img.save(path, optimize=True)


def model_card(m, total, path):
    img, d = canvas()
    r = m["best"]
    raised(d, [K, 32 * K, W - K - 1, H - K - 1])
    logo(img, m["maker"], 8 * K, 40 * K, 3 * K)
    # Long names: fall back to the small font so they never run into the score.
    room = W - 8 * K - d.textlength(f"{r['score']:.1f}", font=HUGE) - 70 * K
    nf = BIG if d.textlength(m["label"], font=BIG) <= room else font(1, 20 * 2)
    text(d, (64 * K, 42 * K if nf is BIG else 48 * K), m["label"], nf, PAL["white"], PAL["dsktop2"])
    text(d, (64 * K, 66 * K), f"{m['maker']}  |  rank {m['rank']} of {total}", SMALL, PAL["dim"])
    text(d, (W - 8 * K, 38 * K), f"{r['score']:.1f}", HUGE, PAL["white"], PAL["looppin"], anchor="ra")
    sunken(d, [5 * K, 92 * K, W - 5 * K - 1, H - 6 * K - 1])
    parts = [("Tonal", r["parts"]["tonal_organization"], 50), ("Development", r["parts"]["development"], 40), ("Dynamics", r["parts"]["dynamics"], 10)]
    for i, (k, v, mx) in enumerate(parts):
        y = 100 * K + i * 18 * K
        text(d, (12 * K, y), k, SMALL, PAL["pattext"])
        x0, x1 = 100 * K, 330 * K
        d.rectangle([x0, y + 2 * K, x1, y + 8 * K], outline=PAL["dsktop2"], width=K)
        d.rectangle([x0 + K, y + 3 * K, x0 + K + round((x1 - x0 - 2 * K) * min(1, v / mx)), y + 7 * K], fill=PAL["pattext"])
        text(d, (W - 12 * K, y), f"{v:.1f}/{mx}", SMALL, PAL["white"], anchor="ra")
    y = 158 * K
    sc = m["scores"]
    att = "  ".join(f"{s:.1f}" for s in sc)
    text(d, (12 * K, y), f"Attempts ({len(sc)})", SMALL, PAL["pattext"])
    text(d, (100 * K, y), att, SMALL, PAL["white"])
    for i, s in enumerate(sc):
        x = W - 12 * K - (len(sc) - i) * 10 * K
        d.rectangle([x, y + 2 * K, x + 7 * K, y + 9 * K], fill=score_color(s))
    text(d, (12 * K, 180 * K), SITE, SMALL, PAL["dim"])
    img.save(path, optimize=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dist", type=Path, required=True)
    args = ap.parse_args()
    data = json.loads((args.dist / "data.json").read_text())
    ms = models(data)
    og = args.dist / "og"
    og.mkdir(exist_ok=True)
    date = str(data.get("generated", ""))[:10]
    home(ms, og / "home.png", date)
    top = ", ".join(f"{m['label']} {m['best']['score']:.1f}" for m in ms[:3])
    desc = f"{len(ms)} AI models write keygen tunes in FastTracker II, scored from the audio. Top: {top}."
    meta = {}
    for route, title in [("/", "Keygen Bench"), ("/tracker", "Keygen Bench: Tracker"), ("/rankings", "Keygen Bench: Rankings"),
                         ("/scoring", "Keygen Bench: How scoring works"), ("/support", "Keygen Bench: Support")]:
        meta[route] = {"title": title, "description": desc, "image": "/dist/og/home.png"}
    for m in ms:
        model_card(m, len(ms), og / f"{m['key']}.png")
        r = m["best"]
        info = {"title": f"{m['label']}: {r['score']:.1f} | Keygen Bench",
                "description": f"Rank {m['rank']} of {len(ms)}. Best of {len(m['scores'])} attempt{'s' if len(m['scores']) != 1 else ''} writing a keygen tune in FastTracker II. Listen to it in the tracker.",
                "image": f"/dist/og/{m['key']}.png"}
        meta[f"/tracker/{m['key']}"] = meta[f"/rankings/{m['key']}"] = info
    (og / "meta.json").write_text(json.dumps(meta, indent=1))
    print(f"wrote {len(ms) + 1} images and {len(meta)} routes to {og}")


if __name__ == "__main__":
    main()
