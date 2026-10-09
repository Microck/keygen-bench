"""Export an assembled publication as a static site for a CDN host (Netlify), with media served elsewhere.

    python web/classic/export_static.py --publication /absolute/publication --out /absolute/static \
        --site-url https://keygen-bench.netlify.app --media-map /absolute/media-map.json

The publication is build.py's output (index.html, app.js, site.js, core/, dist/ with og/ from build_og.py).
`--media-map` is a JSON object mapping each media file name to its absolute URL (MP3 and XM renders, and a
lossless FLAC loop source per WAV, keyed by the FLAC name). data.json's media paths are rewritten to those
URLs, so dist/media/ is not copied; dist/evaluations/ is not read by the site and is dropped; each run's
playback trace moves to dist/traces/<slug>.json, loaded when the tracker opens the run. Every route in dist/og/meta.json gets its own index.html with that
route's preview tags (static hosts cannot inject them per request); other app routes fall back to the
root index.html through netlify.toml. Files are hard-linked where possible; the output must not exist.
"""
import argparse
import json
import os
import re
import shutil
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from serve import APP_ROUTES, with_og

STATIC_HEADERS = """
[[headers]]
  for = "/*"
  [headers.values]
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"
    X-Frame-Options = "SAMEORIGIN"

[[headers]]
  for = "/dist/*"
  [headers.values]
    Cache-Control = "public, max-age=300, must-revalidate"

[[headers]]
  for = "/core/fonts/*"
  [headers.values]
    Cache-Control = "public, max-age=604800"

[[headers]]
  for = "/core/ft2gfx/*"
  [headers.values]
    Cache-Control = "public, max-age=604800"
"""


SITE_NAME = "Keygen Bench"
SITE_SUMMARY = ("Keygen Bench asks AI models to compose a keygen-style chiptune in FastTracker II, with no network and a "
                "Bash tool, three independent attempts each at its highest declared reasoning tier. A trusted FT2 render of "
                "each XM module supplies audio evidence for a versioned craft score (tonal organization, development, dynamics, signal, "
                "noise, loop and duration). Models are ranked by their best of three attempts.")


def model_name(name: str) -> str:
    return re.sub(r"\s*\((?:[^()]*,\s*)?attempt\s+\d+\)\s*$|\s*\(max-tier\)\s*$", "", name, flags=re.I)


def leaderboard(data: dict) -> list[dict]:
    """Ranked models: best-of-3 row plus every attempt's score, in rank order."""
    attempts = {}
    for run in data["runs"]:
        attempts.setdefault(model_name(run["name"]), []).append(run)
    rows = []
    for run in sorted((r for r in data["runs"] if r.get("ranked")), key=lambda r: r["rank"]):
        name = model_name(run["name"])
        scores = sorted((r["provenance"].get("attempt_ordinal") or 0, r["score"]) for r in attempts[name])
        rows.append({"rank": run["rank"], "name": name, "maker": run["maker"], "score": run["score"],
                     "attempts": [score for _, score in scores], "slug": run["slug"]})
    return rows


def seo_head(route: str, site_url: str, info: dict, board: list[dict], generated: str) -> str:
    """Canonical URL, robots and schema.org JSON-LD (the results as a Dataset; the ranking as an ItemList)."""
    url = site_url + ("" if route == "/" else route)
    graph = [{"@type": "WebSite", "@id": site_url + "/#site", "name": SITE_NAME, "url": site_url + "/", "description": SITE_SUMMARY},
             {"@type": "Dataset", "@id": site_url + "/#results", "name": "Keygen Bench results", "description": SITE_SUMMARY,
              "url": site_url + "/rankings", "dateModified": generated, "creator": {"@type": "Person", "name": "Microck", "url": "https://github.com/Microck"},
              "isAccessibleForFree": True, "keywords": ["AI benchmark", "LLM benchmark", "FastTracker II", "chiptune", "keygen music", "XM module"],
              "variableMeasured": "versioned craft score (0-100)",
              "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": site_url + "/dist/data.json"}]}]
    if route in ("/", "/rankings"):
        graph.append({"@type": "ItemList", "name": "Keygen Bench ranking (best of 3)", "numberOfItems": len(board),
                      "itemListElement": [{"@type": "ListItem", "position": row["rank"], "name": f"{row['name']} ({row['maker']}): {row['score']:.1f}"}
                                          for row in board]})
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, separators=(",", ":")).replace("</", "<\\/")
    return (f'<link rel="canonical" href="{escape(url)}">\n<meta name="robots" content="index,follow">\n'
            f'<meta name="theme-color" content="#4D619A">\n<script type="application/ld+json">{ld}</script>\n')


def seo_body(route: str, info: dict, board: list[dict]) -> str:
    """Readable content for crawlers and AI agents that do not run the app's JavaScript."""
    table = "".join(f"<tr><td>{r['rank']}</td><td>{escape(r['name'])}</td><td>{escape(r['maker'])}</td><td>{r['score']:.1f}</td>"
                    f"<td>{' / '.join(f'{s:.1f}' for s in r['attempts'])}</td></tr>" for r in board)
    ranking = (f"<table><caption>Ranking, best of 3 attempts</caption><tr><th>Rank</th><th>Model</th><th>Maker</th>"
               f"<th>Best score</th><th>Attempt scores</th></tr>{table}</table>")
    full = route in ("/", "/rankings") or route.startswith(("/rankings", "/tracker"))
    return (f"<noscript><main><h1>{escape(info['title'])}</h1><p>{escape(info['description'])}</p><p>{escape(SITE_SUMMARY)}</p>"
            f"{ranking if full else ''}<p><a href=\"/rankings\">Rankings</a> | <a href=\"/tracker\">Tracker</a> | "
            f"<a href=\"/scoring\">Scoring</a> | <a href=\"/support\">Support</a></p></main></noscript>\n")


def site_files(out: Path, site_url: str, meta: dict, board: list[dict], generated: str) -> None:
    """robots.txt, sitemap.xml and llms.txt (a plain-text summary and ranking for AI agents)."""
    day = generated[:10]
    urls = "".join(f"<url><loc>{escape(site_url + ('' if route == '/' else route))}</loc><lastmod>{day}</lastmod></url>" for route in meta)
    (out / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {site_url}/sitemap.xml\n")
    lines = [f"# {SITE_NAME}", "", f"> {SITE_SUMMARY}", "",
             f"Results snapshot: {day}. Full data: {site_url}/dist/data.json. Source and every run: https://github.com/Microck/keygen-bench", "",
             "## Pages", "", f"- [Rankings]({site_url}/rankings): best-of-3 ranking with every attempt",
             f"- [Tracker]({site_url}/tracker): play each module in an FT2-style pattern view",
             f"- [Scoring]({site_url}/scoring): how craft scores audio and XM structure", f"- [Support]({site_url}/support): costs and how to fund or contribute runs", "",
             "## Ranking (best of 3)", "", "| Rank | Model | Maker | Best | Attempts |", "| --- | --- | --- | --- | --- |"]
    # Model pages are keyed by model (see build_og.py); their card title starts with the model's label.
    pages = {meta[route]["title"].split(":")[0]: route for route in meta if route.startswith("/tracker/") and route.count("/") == 2}
    lines += [f"| {r['rank']} | [{r['name']}]({site_url}{pages.get(r['name'], '/tracker')}) | {r['maker']} | {r['score']:.1f} | "
              f"{' / '.join(f'{s:.1f}' for s in r['attempts'])} |" for r in board]
    (out / "llms.txt").write_text("\n".join(lines) + "\n")


def media_url(path: str, mapping: dict, kind: str) -> str:
    name = Path(path).name
    if kind == "wav":
        name = Path(name).with_suffix(".flac").name
    if name not in mapping:
        raise ValueError(f"No hosted URL for {name}")
    return mapping[name]


def link_or_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def export(publication: Path, out: Path, site_url: str, mapping: dict, redirect_from: list[str] = (), host: str = "netlify") -> None:
    if out.exists():
        raise ValueError("Use a new output directory")
    site_url = site_url.rstrip("/")
    for path in publication.rglob("*"):
        rel = path.relative_to(publication)
        if path.is_symlink():
            raise ValueError(f"{rel}: public files must not be symlinks")
        # dist/media is hosted elsewhere; dist/evaluations (full evaluation records) is not read by the site.
        if (path.is_file() and rel.parts[:2] not in (("dist", "media"), ("dist", "evaluations"))
                and rel != Path("dist/data.json") and "__pycache__" not in rel.parts):
            link_or_copy(path, out / rel)
    data = json.loads((publication / "dist/data.json").read_text())
    traces = out / "dist/traces"
    traces.mkdir(parents=True)
    for run in data["runs"]:
        media = run.get("media") or {}
        media.pop("evaluation", None)
        for kind in ("xm", "audio", "wav"):
            if media.get(kind):
                media[kind] = media_url(media[kind], mapping, kind)
        # Playback traces are ~70% of data.json and only the tracker needs them: one file per run, loaded on open.
        if run.get("trace") is not None:
            (traces / f"{run['slug']}.json").write_text(json.dumps(run.pop("trace"), separators=(",", ":")) + "\n")
            media["trace"] = f"traces/{run['slug']}.json"
    (out / "dist/data.json").write_text(json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n")
    meta = json.loads((publication / "dist/og/meta.json").read_text())
    shell = (publication / "index.html").read_text(encoding="utf-8")
    board = leaderboard(data)
    generated = str(data.get("generated") or datetime.now(timezone.utc).isoformat())
    (out / "index.html").unlink()
    for route in meta:
        # "/tracker/x" -> tracker/x.html: Netlify serves it at the bare path (a directory index would 301 to "/tracker/x/").
        target = out / (route.strip("/") + ".html") if route != "/" else out / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        page = with_og(shell, meta, route, site_url)
        page = page.replace("</head>", seo_head(route, site_url, meta[route], board, generated) + "</head>", 1)
        page = page.replace("<body>\n", "<body>\n" + seo_body(route, meta[route], board), 1)
        target.write_text(page, encoding="utf-8")
    site_files(out, site_url, meta, board, generated)
    redirects = "\n".join(f'[[redirects]]\n  from = "/{route}/*"\n  to = "/index.html"\n  status = 200\n'
                          for route in sorted(APP_ROUTES))
    # Other hostnames of the same deployment (e.g. the *.netlify.app default) move permanently to --site-url.
    canonical = "".join(f'[[redirects]]\n  from = "https://{host}/*"\n  to = "{site_url}/:splat"\n  status = 301\n  force = true\n\n'
                        for host in redirect_from)
    if host == "github-pages":
        # GitHub Pages serves "/tracker/x" from tracker/x.html and has no rewrites: unknown app routes get
        # 404.html, a copy of the app shell (the app routes by path). CNAME names the custom domain;
        # .nojekyll serves files as they are. Response headers cannot be configured there.
        shutil.copy2(out / "index.html", out / "404.html")
        (out / "CNAME").write_text(re.sub(r"^https?://", "", site_url) + "\n")
        (out / ".nojekyll").write_text("")
    else:
        (out / "netlify.toml").write_text(f"# Generated by web/classic/export_static.py\n\n{canonical}{redirects}{STATIC_HEADERS}")
    print(f"{len(meta)} routes with preview tags, {len(data['runs'])} runs with hosted media -> {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--publication", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--site-url", required=True, help="Public origin used in og:url and og:image")
    parser.add_argument("--media-map", type=Path, required=True)
    parser.add_argument("--redirect-from", action="append", default=[], metavar="HOST",
                        help="Another hostname of this deployment to redirect permanently to --site-url (Netlify)")
    parser.add_argument("--host", choices=("netlify", "github-pages"), default="netlify",
                        help="netlify: netlify.toml rewrites, redirects and headers; github-pages: 404.html shell, CNAME, .nojekyll")
    args = parser.parse_args()
    export(args.publication.resolve(), args.out.resolve(), args.site_url, json.loads(args.media_map.read_text()), args.redirect_from, args.host)
