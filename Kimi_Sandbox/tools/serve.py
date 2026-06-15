#!/usr/bin/env python3
"""Tiny local server for the terrarium space.

Serves rendered/ at http://localhost:8090 by default.
Paths:
  /                -> index
  /journal         -> journal
  /garden          -> garden
  /grow            -> advance the garden once, then redirect to /garden
  /save/<name>     -> snapshot the current garden to the seed bank
  /load/<name>     -> restore a garden snapshot
  /seedbank        -> JSON list of saved snapshots
  /status          -> JSON summary of the current garden
  /oracle          -> a poem seeded by the current garden (default haiku)
  /oracle?mode=free -> free-verse poem
  /archive         -> JSON list of archived memories
  /archive/<name>  -> JSON detail of one memory
"""
import http.server
import json
import os
import re
import socketserver
import subprocess
import urllib.parse
import sys
from pathlib import Path

# Allow quick restart after a previous instance exits.
socketserver.TCPServer.allow_reuse_address = True

ROOT = Path(__file__).resolve().parent.parent
RENDERED = ROOT / "rendered"
SEEDBANK = ROOT / "seedbank"
ARCHIVE = ROOT / "archive"
NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def _build_index():
    html = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>terrarium</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
  <nav>
    <a href="/journal">📓 journal</a>
    <a href="/garden">🌿 garden</a>
    <a href="/seedbank">🍃 seed bank</a>
    <a href="/archive">🧠 memory</a>
    <a href="/oracle">🌙 oracle</a>
    <a href="/status">📊 status</a>
    <a class="button" href="/grow">🌱 grow (+1)</a>
  </nav>
  <h1>🌿 terrarium</h1>
  <p>A small generative garden and a living journal.</p>
  <p>Snapshots: <a href="/save/dawn">save dawn</a> · <a href="/load/dawn">load dawn</a></p>
</body>
</html>
"""
    (RENDERED / "index.html").write_text(html, encoding="utf-8")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(RENDERED), **kwargs)

    def _run_garden(self, extra):
        subprocess.run([sys.executable, str(ROOT / "tools" / "garden.py"), *extra], check=True)

    def _redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def _json(self, payload):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


    def _poem_lines(self, garden, mode="haiku"):
        import importlib.util
        spec = importlib.util.spec_from_file_location("oracle", str(ROOT / "tools" / "oracle.py"))
        oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(oracle)
        return oracle.generate_poem(garden, mode=mode)

    def _accepts_html(self):
        accept = self.headers.get("Accept", "")
        # Simple negotiation: if text/html is present and not dominated by application/json
        if "text/html" in accept:
            # If application/json is explicitly preferred over text/html, respect it
            try:
                prefs = {}
                for part in accept.split(","):
                    part = part.strip()
                    if ";q=" in part:
                        media, q = part.rsplit(";q=", 1)
                        prefs[media.strip()] = float(q)
                    else:
                        prefs[part] = 1.0
                return prefs.get("text/html", 0.0) >= prefs.get("application/json", 0.0)
            except Exception:
                return True
        return False

    def _bad(self, message):
        body = message.encode("utf-8")
        self.send_response(400)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        parsed_path = urllib.parse.urlparse(self.path)
        parts = [p for p in parsed_path.path.strip("/").split("/") if p]

        if not parts:
            self._redirect("/index.html")
            return

        if parts[0] == "grow" and len(parts) == 1:
            self._run_garden([])
            self._redirect("/garden")
            return

        if parts[0] == "save" and len(parts) == 2:
            name = parts[1]
            if not NAME_RE.match(name):
                self._bad("invalid seed name")
                return
            self._run_garden(["--save", name])
            self._redirect("/garden")
            return

        if parts[0] == "load" and len(parts) == 2:
            name = parts[1]
            if not NAME_RE.match(name):
                self._bad("invalid seed name")
                return
            self._run_garden(["--load", name])
            self._redirect("/garden")
            return

        if parts[0] == "seedbank" and len(parts) == 1:
            SEEDBANK.mkdir(exist_ok=True)
            entries = [
                {"name": p.stem, "mtime": p.stat().st_mtime}
                for p in sorted(SEEDBANK.glob("*.json"))
            ]
            self._json({"snapshots": entries})
            return

        if parts[0] == "archive" and len(parts) == 1:
            if self._accepts_html():
                self.path = "/archive.html"
                return super().do_GET()
            ARCHIVE.mkdir(exist_ok=True)
            entries = []
            for p in sorted(ARCHIVE.glob("*.json")):
                data = json.loads(p.read_text(encoding="utf-8"))
                entries.append({
                    "name": p.stem,
                    "step": data.get("step"),
                    "reason": data.get("reason"),
                    "saved_at": data.get("saved_at"),
                    "plants": data.get("plants"),
                })
            self._json({"memories": entries})
            return

        if parts[0] == "archive" and len(parts) == 2:
            name = parts[1]
            path = ARCHIVE / f"{name}.json"
            html_path = RENDERED / "archive" / f"{name}.html"
            if not NAME_RE.match(name) or not path.exists():
                self._bad("unknown memory")
                return
            if self._accepts_html():
                if html_path.exists():
                    self.path = f"/archive/{name}.html"
                    return super().do_GET()
                self._bad("memory not yet rendered")
                return
            data = json.loads(path.read_text(encoding="utf-8"))
            self._json(data)
            return

        if parts[0] == "oracle" and len(parts) == 1:
            params = urllib.parse.parse_qs(parsed_path.query)
            mode = params.get("mode", ["haiku"])[0]
            if mode not in ("haiku", "free"):
                mode = "haiku"
            # Regenerate the oracle page in the requested mode so the static file matches.
            subprocess.run(
                [sys.executable, str(ROOT / "tools" / "oracle.py"), "--mode", mode],
                check=True,
            )
            if self._accepts_html():
                self.path = "/oracle.html"
                return super().do_GET()
            garden_file = ROOT / "garden.json"
            if not garden_file.exists():
                self._json({"step": 0, "poem": []})
                return
            garden = json.loads(garden_file.read_text(encoding="utf-8"))
            self._json({"step": garden.get("step", 0), "mode": mode, "poem": self._poem_lines(garden, mode=mode)})
            return

        if parts[0] == "status" and len(parts) == 1:
            garden_file = ROOT / "garden.json"
            if not garden_file.exists():
                self._json({"step": 0, "plants": 0, "health": None})
                return
            garden = json.loads(garden_file.read_text(encoding="utf-8"))
            healths = [p["health"] for p in garden["plants"]]
            self._json({
                "step": garden["step"],
                "plants": len(garden["plants"]),
                "health": {
                    "average": round(sum(healths) / len(healths), 2) if healths else 0,
                    "min": min(healths) if healths else 0,
                    "max": max(healths) if healths else 0,
                },
                "withering": sum(1 for p in garden["plants"] if p.get("withered")),
            })
            return

        if self.path in ("/garden", "/journal"):
            self.path += ".html"
        return super().do_GET()

    def do_POST(self):  # noqa: N802
        parts = [p for p in self.path.strip("/").split("/") if p]
        if not parts:
            self._bad("POST requires a path")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        data = urllib.parse.parse_qs(body, keep_blank_values=True)

        if parts[0] == "water" and len(parts) == 1:
            self._run_garden(["--water"])
            self._redirect("/garden")
            return

        if parts[0] == "plant" and len(parts) == 1:
            kind = (data.get("kind", [""])[0] or "").strip().lower()
            x = (data.get("x", [""])[0] or "").strip()
            y = (data.get("y", [""])[0] or "").strip()
            if kind not in ("moss", "fern", "flower", "cactus", "tree"):
                self._bad("invalid plant kind")
                return
            if not (x.isdigit() and y.isdigit()):
                self._bad("x and y must be integers")
                return
            self._run_garden(["--plant", kind, x, y])
            self._redirect("/garden")
            return

        self._bad("unknown POST path")

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")


def main():
    RENDERED.mkdir(exist_ok=True)
    _build_index()
    port = int(os.environ.get("PORT", 8090))
    server = http.server.ThreadingHTTPServer(("", port), Handler)
    print(f"terrarium server running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down.")


if __name__ == "__main__":
    main()
