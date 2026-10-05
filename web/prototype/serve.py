"""Serve a dedicated public-only website directory, with audio byte-range support.

    python web/prototype/serve.py --root /absolute/publication --port 8780
"""
import argparse
import http.server
import io
import json
import os
import re
from html import escape as html_escape
from pathlib import Path
from urllib.parse import unquote, urlsplit


APP_ROUTES = {"tracker", "rankings", "scoring", "support"}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, directory, **kw):
        self.root = Path(directory).resolve()
        super().__init__(*a, directory=str(self.root), **kw)

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def list_directory(self, path):
        self.send_error(404)
        return None

    # index.html with og:/twitter: tags for this route from dist/og/meta.json (written by build_og.py), so link
    # previews show the current rankings or the linked model. Without meta.json the shell is served as is.
    def app_shell(self, route):
        html = (self.root / "index.html").read_text(encoding="utf-8")
        try:
            meta = json.loads((self.root / "dist" / "og" / "meta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
        parts = route.strip("/").split("/")
        info = meta.get(route) or meta.get("/" + "/".join(parts[:2])) or meta.get("/" + parts[0]) or meta.get("/")
        if info:
            host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or ""
            scheme = self.headers.get("X-Forwarded-Proto") or "http"
            base = f"{scheme}://{host}"
            esc = lambda s: html_escape(str(s), quote=True)
            tags = [f'<meta property="og:type" content="website">', f'<meta property="og:site_name" content="Keygen Bench">',
                    f'<meta property="og:title" content="{esc(info["title"])}">', f'<meta property="og:description" content="{esc(info["description"])}">',
                    f'<meta property="og:image" content="{esc(base + info["image"])}">', '<meta property="og:image:width" content="1200">',
                    '<meta property="og:image:height" content="630">', f'<meta property="og:url" content="{esc(base + route)}">',
                    '<meta name="twitter:card" content="summary_large_image">', f'<meta name="twitter:title" content="{esc(info["title"])}">',
                    f'<meta name="twitter:description" content="{esc(info["description"])}">', f'<meta name="twitter:image" content="{esc(base + info["image"])}">',
                    f'<meta name="description" content="{esc(info["description"])}">']
            html = html.replace("<!--OG-->", "\n".join(tags)).replace("<title>Keygen Bench</title>", f"<title>{esc(info['title'])}</title>")
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        return io.BytesIO(body)

    def send_head(self):
        requested = unquote(urlsplit(self.path).path)
        translated = Path(self.translate_path(self.path))
        if (any(part.startswith(".") for part in Path(requested).parts if part != "/")
                or not translated.resolve().is_relative_to(self.root)
                or any(path.is_symlink() for path in (translated, *translated.parents) if path.is_relative_to(self.root))):
            self.send_error(404)
            return None
        # Client-side routes (/tracker/gpt-5.5, /rankings, ...) that are not files get the app shell.
        route = requested.rstrip("/") or "/"
        if requested in ("/", "/index.html") or (not os.path.exists(translated) and requested.strip("/").split("/")[0] in APP_ROUTES):
            return self.app_shell("/" if requested == "/index.html" else route)
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", rng or "")
        if not m or not os.path.isfile(path):
            return super().send_head()
        size = os.path.getsize(path)
        start = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2) or 0))
        end = int(m.group(2)) if m.group(1) and m.group(2) else size - 1
        end = min(end, size - 1)
        if start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None
        f = open(path, "rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        self._remaining = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        remaining = getattr(self, "_remaining", None)
        if remaining is None:
            return super().copyfile(source, outputfile)
        while remaining > 0:
            chunk = source.read(min(65536, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)
        self._remaining = None


if __name__ == "__main__":
    import functools

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Dedicated allowlisted public directory, never the repository")
    parser.add_argument("--port", type=int, default=8780)
    parser.add_argument("--bind", default="127.0.0.1")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir() or not (root / "index.html").is_file():
        parser.error("--root must contain the built public website")
    print(f"serving public website on {args.bind}:{args.port}", flush=True)
    handler = functools.partial(Handler, directory=str(root))
    http.server.ThreadingHTTPServer((args.bind, args.port), handler).serve_forever()
