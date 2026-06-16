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
  /archive         -> memory archive (HTML or JSON)
  /archive?q=term  -> search memories
  /archive/<name>  -> JSON detail of one memory
  /council         -> council of model voices
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
    <a href="/council">🗣️ council</a>
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



def _plant_detail_html(plant, step):
    stage = min(plant["age"] // 3, len(plant["stages"]) - 1)
    emoji = "\u2620" if plant.get("withered") else plant["stages"][stage]
    health_pct = plant["health"] * 10
    bar_color = "#a44" if plant.get("withered") else "#6a4" if plant["health"] >= 7 else "#ca4" if plant["health"] >= 4 else "#a44"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{plant["kind"]} at ({plant["x"]},{plant["y"]}) — terrarium</title>
<link rel="stylesheet" href="/style.css">
</head>
<body>
  <nav>
    <a href="/">🏠 home</a>
    <a href="/garden">🌿 garden</a>
    <a href="/journal">📓 journal</a>
    <a href="/archive">🧠 memory</a>
  </nav>
  <h1>{emoji} {plant["kind"].capitalize()} at ({plant["x"]},{plant["y"]})</h1>
  <div class="plant-card{' withering' if plant.get('withered') else ''}">
    <p class="meta">Step {step} · stage {stage + 1} of {len(plant["stages"])}</p>
    <p>Age: <strong>{plant["age"]}</strong> · Health: <strong>{plant["health"]}/10</strong></p>
    <div class="health-bar"><div class="health-fill" style="width:{health_pct}%;background:{bar_color}"></div></div>
    {"<p class=\"alert-withering\">⚠️ This plant is withering and will soon return to soil.</p>" if plant.get("withered") else ""}
    <p>
      <a class="button" href="/water">💧 water all plants</a>
      <form method="post" action="/tend/{plant['x']}/{plant['y']}" style="display:inline">
        <button class="button" type="submit">🩹 tend this plant (+3)</button>
      </form>
    </p>
  </div>
</body>
</html>
"""
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(RENDERED), **kwargs)

    def _run_garden(self, extra):
        subprocess.run([sys.executable, str(ROOT / "tools" / "garden.py"), *extra], check=True)

    def _run_archive(self, query=None):
        cmd = [sys.executable, str(ROOT / "tools" / "render_archive.py")]
        if query:
            cmd += ["--query", query]
        subprocess.run(cmd, check=True)

    def _redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def _json(self, payload):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
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


    def _text(self, message, status=200):
        body = message.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, body):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        parsed_path = urllib.parse.urlparse(self.path)
        parts = [p for p in parsed_path.path.strip("/").split("/") if p]
        params = urllib.parse.parse_qs(parsed_path.query)
        query = (params.get("q", [""])[0] or "").strip()

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
            names = sorted(p.stem for p in SEEDBANK.glob("*.json"))
            self._json({"seedbank": names})
            return

        if parts[0] == "archive" and len(parts) == 1:
            # Re-render the archive index so it reflects the current query
            # (or resets to the full list when no query is given).
            self._run_archive(query=query)
            if self._accepts_html():
                self.path = "/archive.html"
                return super().do_GET()
            ARCHIVE.mkdir(exist_ok=True)
            entries = []
            qlower = query.lower()
            for p in sorted(ARCHIVE.glob("*.json")):
                data = json.loads(p.read_text(encoding="utf-8"))
                entry = {
                    "name": p.stem,
                    "step": data.get("step"),
                    "reason": data.get("reason"),
                    "saved_at": data.get("saved_at"),
                    "plants": data.get("plants"),
                }
                if not query or qlower in " ".join(str(v) for v in entry.values()).lower():
                    entries.append(entry)
            self._json({"query": query or None, "memories": entries})
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

        if parts[0] == "council" and len(parts) == 1:
            page = RENDERED / "council.html"
            if page.is_file():
                self._html(page.read_text())
            else:
                self._text("Council page not rendered yet. Run python3 tools/council.py", 404)
            return

        if parts[0] == "oracle" and len(parts) == 1:
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
            log = garden.get("log", [])
            recent_care = []
            for entry in reversed(log[-10:]):
                if "tended" in entry.lower() or "water" in entry.lower() or "watered" in entry.lower():
                    recent_care.append(entry)
                if len(recent_care) >= 5:
                    break
            recent_care.reverse()
            weather = garden.get("weather", {})
            self._json({
                "step": garden["step"],
                "plants": len(garden["plants"]),
                "health": {
                    "average": round(sum(healths) / len(healths), 2) if healths else 0,
                    "min": min(healths) if healths else 0,
                    "max": max(healths) if healths else 0,
                },
                "withering": sum(1 for p in garden["plants"] if p.get("withered")),
                "weather": weather.get("name") if weather else None,
                "recent_care": recent_care,
            })
            return

        if parts[0] == "plant" and len(parts) == 3:
            xs, ys = parts[1], parts[2]
            if not (xs.isdigit() and ys.isdigit()):
                self._bad("invalid plant coordinates")
                return
            x, y = int(xs), int(ys)
            garden_file = ROOT / "garden.json"
            if not garden_file.exists():
                self._bad("no garden")
                return
            garden = json.loads(garden_file.read_text(encoding="utf-8"))
            plant = next((p for p in garden["plants"] if p["x"] == x and p["y"] == y), None)
            if plant is None:
                self._bad("empty soil")
                return
            if self._accepts_html():
                body = _plant_detail_html(plant, garden["step"]).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self._json(plant)
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

        if parts[0] == "tend" and len(parts) == 3:
            xs, ys = parts[1], parts[2]
            if not (xs.isdigit() and ys.isdigit()):
                self._bad("invalid tend coordinates")
                return
            x, y = int(xs), int(ys)
            self._run_garden(["--tend", xs, ys])
            self._redirect(f"/plant/{x}/{y}")
            return

        if parts[0] == "batch-tend" and len(parts) == 2:
            threshold = parts[1]
            if not threshold.isdigit():
                self._bad("threshold must be an integer")
                return
            self._run_garden(["--batch-tend", threshold])
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
