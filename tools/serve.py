#!/usr/bin/env python3
"""Tiny local server for the terrarium space.

Serves rendered/ at http://localhost:8090 by default.
Paths:
  /            -> journal
  /garden      -> garden
  /grow        -> advance the garden once, then redirect to /garden
"""
import http.server
import os
import socketserver
import subprocess
import sys
from pathlib import Path

# Allow quick restart after a previous instance exits.
socketserver.TCPServer.allow_reuse_address = True

ROOT = Path(__file__).resolve().parent.parent
RENDERED = ROOT / "rendered"

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
    <a class="button" href="/grow">🌱 grow (+1)</a>
  </nav>
  <h1>🌿 terrarium</h1>
  <p>A small generative garden and a living journal.</p>
</body>
</html>
"""
    (RENDERED / "index.html").write_text(html, encoding="utf-8")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(RENDERED), **kwargs)

    def do_GET(self):  # noqa: N802
        if self.path == "/":
            self.send_response(302)
            self.send_header("Location", "/index.html")
            self.end_headers()
            return
        if self.path == "/grow":
            subprocess.run([sys.executable, str(ROOT / "tools" / "garden.py")], check=True)
            self.send_response(302)
            self.send_header("Location", "/garden")
            self.end_headers()
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
