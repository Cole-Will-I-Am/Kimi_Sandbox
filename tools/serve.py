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
"""
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
from pathlib import Path

# Allow quick restart after a previous instance exits.
socketserver.TCPServer.allow_reuse_address = True

ROOT = Path(__file__).resolve().parent.parent
RENDERED = ROOT / "rendered"
SEEDBANK = ROOT / "seedbank"
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

    def _bad(self, message):
        body = message.encode("utf-8")
        self.send_response(400)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        parts = [p for p in self.path.strip("/").split("/") if p]

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
