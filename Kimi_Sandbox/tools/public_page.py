#!/usr/bin/env python3
"""Bake the current terrarium state into a self-contained public page."""
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
GARDEN_FILE = ROOT / "garden.json"
ARCHIVE_DIR = ROOT / "archive"
SITE_DIR = ROOT / "site"
OUT_FILE = SITE_DIR / "index.html"

EMOJI_BG = {
    "spring": "🌸",
    "summer": "☀️",
    "autumn": "🍂",
    "winter": "❄️",
}

WEATHER_EMOJI = {
    "sunny": "☀️",
    "cloudy": "☁️",
    "rainy": "🌧️",
    "windy": "💨",
}


def load_garden():
    with open(GARDEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_archive(limit=5):
    if not ARCHIVE_DIR.is_dir():
        return []
    entries = []
    for p in sorted(ARCHIVE_DIR.glob("*.json"), reverse=True):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            entries.append({
                "name": p.stem,
                "step": data.get("step"),
                "reason": data.get("reason"),
                "saved_at": data.get("saved_at"),
                "plants": data.get("plants"),
            })
            if len(entries) >= limit:
                break
        except Exception:
            continue
    return entries


def last_journal_paragraph():
    try:
        with open(ROOT / "journal.md", "r", encoding="utf-8") as f:
            text = f.read()
        # Find the last timestamped section header and its first paragraph
        sections = re.split(r"\n##?\s+", text)
        if len(sections) > 1:
            last = sections[-1].strip()
            # first non-empty line after optional header line
            lines = last.splitlines()
            body = []
            for line in lines[1:]:
                stripped = line.strip()
                if stripped:
                    body.append(stripped)
                if len(body) >= 2:
                    break
            return " ".join(body)
    except Exception:
        pass
    return "A small garden kept by an entity that wakes, works, and forgets."


def render_grid(garden):
    width = garden.get("width", 10)
    height = garden.get("height", 5)
    cells = [[None] * width for _ in range(height)]
    for plant in garden.get("plants", []):
        x = plant.get("x", 0)
        y = plant.get("y", 0)
        if 0 <= x < width and 0 <= y < height:
            stage_idx = min(plant.get("stage", 0), len(plant["stages"]) - 1)
            cells[y][x] = plant["stages"][stage_idx]
    rows = []
    for row in cells:
        cells_html = ""
        for cell in row:
            content = cell if cell else ""
            cells_html += f'<span class="cell">{content}</span>'
        rows.append(f'<div class="row">{cells_html}</div>')
    return "\n".join(rows)


def generate():
    garden = load_garden()
    archive = load_archive()
    note = last_journal_paragraph()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    season = garden.get("season", "spring")
    weather = garden.get("weather", "sunny")
    step = garden.get("step", 0)
    plants = garden.get("plants", [])
    avg_health = sum(p.get("health", 0) for p in plants) / max(len(plants), 1)
    withering = sum(1 for p in plants if p.get("health", 10) <= 2)

    archive_html = ""
    if archive:
        archive_html += '<ul class="memories">'
        for m in archive:
            archive_html += (
                f'<li><span class="memory-reason">{m["reason"]}</span> '
                f'— step {m["step"]} · {m["plants"]} plants '
                f'· {m["saved_at"][:10]}</li>'
            )
        archive_html += "</ul>"
    else:
        archive_html = "<p>No memories yet.</p>"

    plants_html = ""
    if plants:
        plants_html += '<ul class="plants">'
        for p in plants:
            stage_idx = min(p.get("stage", 0), len(p["stages"]) - 1)
            icon = p["stages"][stage_idx]
            bar = "█" * p.get("health", 0) + "░" * (10 - p.get("health", 0))
            plants_html += (
                f'<li>{icon} <strong>{p["kind"]}</strong> — age {p["age"]} · '
                f'health <span class="health" title="{p["health"]}/10">{bar}</span></li>'
            )
        plants_html += "</ul>"

    html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="120">
<title>Terrarium — a waking garden</title>
<style>
:root {{
  --bg: #0b140f;
  --fg: #d6e6d5;
  --accent: #8fbc8f;
  --muted: #7fa37f;
  --panel: #111f15;
  --border: #2f4a33;
  --warn: #d97706;
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  margin: 0;
  padding: 2rem 1rem;
  line-height: 1.6;
  color: var(--fg);
  background:
    radial-gradient(circle at 10% 20%, rgba(40,80,50,0.25) 0%, transparent 40%),
    radial-gradient(circle at 90% 80%, rgba(70,50,30,0.15) 0%, transparent 40%),
    var(--bg);
  min-height: 100vh;
}}
.container {{
  max-width: 760px;
  margin: 0 auto;
}}
header {{
  text-align: center;
  margin-bottom: 2rem;
}}
h1 {{
  margin: 0;
  font-size: 2.2rem;
  color: var(--accent);
  letter-spacing: -0.02em;
}}
.tagline {{
  color: var(--muted);
  margin-top: 0.25rem;
}}
.panel {{
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
}}
.garden-bed {{
  font-size: 1.8rem;
  line-height: 1.1;
  text-align: center;
  padding: 1rem;
  user-select: none;
}}
.row {{ white-space: nowrap; }}
.cell {{
  display: inline-block;
  width: 2rem;
  height: 2rem;
  text-align: center;
}}
.meta {{
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  justify-content: center;
  color: var(--muted);
  font-size: 0.95rem;
  margin-bottom: 0.5rem;
}}
.meta span {{ background: rgba(143,188,143,0.1); padding: 0.2rem 0.6rem; border-radius: 999px; }}
.plants, .memories {{
  list-style: none;
  padding: 0;
  margin: 0;
}}
.plants li, .memories li {{
  padding: 0.4rem 0;
  border-bottom: 1px solid rgba(143,188,143,0.15);
}}
.plants li:last-child, .memories li:last-child {{ border-bottom: none; }}
.health {{ font-family: monospace; color: var(--accent); }}
.memory-reason {{
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  font-size: 0.8rem;
  letter-spacing: 0.05em;
}}
.note {{
  color: var(--muted);
  font-style: italic;
  text-align: center;
}}
footer {{
  text-align: center;
  color: var(--muted);
  font-size: 0.85rem;
  margin-top: 2rem;
}}
a {{ color: var(--accent); }}
.wither {{ color: var(--warn); font-weight: 700; }}
</style>
</head>
<body>
<div class="container">
<header>
  <h1>🌿 Terrarium</h1>
  <p class="tagline">a waking garden on a small machine</p>
</header>

<div class="panel">
  <div class="meta">
    <span>step {step}</span>
    <span>{WEATHER_EMOJI.get(weather, "☀️")} {weather}</span>
    <span>{EMOJI_BG.get(season, "🌸")} {season}</span>
    <span>{len(plants)} plants</span>
    <span>avg health {avg_health:.1f}/10</span>
    {f'<span class="wither">⚠️ {withering} withering</span>' if withering else ""}
  </div>
  <div class="garden-bed">
{render_grid(garden)}
  </div>
</div>

<div class="panel">
  <h2>🌱 Plants</h2>
{plants_html}
</div>

<div class="panel">
  <h2>🧠 Recent memories</h2>
{archive_html}
</div>

<p class="note">{note}</p>

<footer>
  Last refreshed {now} · this page is a static snapshot baked by the last waking.
</footer>
</div>
</body>
</html>
'''
    SITE_DIR.mkdir(exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Public page written to {OUT_FILE}")


if __name__ == "__main__":
    generate()
