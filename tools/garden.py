#!/usr/bin/env python3
"""A small generative garden for /srv/terrarium/space.

Each run ages every plant by one step and may plant a new seedling.
State lives in garden.json; a pretty view is written to rendered/garden.html.

Usage:
    python3 tools/garden.py           # let the garden age one step
    python3 tools/garden.py --water   # water every plant, restoring health
    python3 tools/garden.py --plant cactus 3 4  # plant a seedling at x=3, y=4
    python3 tools/garden.py --save dawn           # snapshot current garden
    python3 tools/garden.py --load dawn           # restore a snapshot
"""
import argparse
import json
import pathlib
import random
import re
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
GARDEN_FILE = ROOT / "garden.json"
OUT_FILE = ROOT / "rendered" / "garden.html"
SEEDBANK_DIR = ROOT / "seedbank"

KINDS = [
    {"kind": "moss", "stages": ["·", "🌱", "🌿", "🍃"]},
    {"kind": "fern", "stages": ["·", "🌱", "🌿", "🌿", "🌴"]},
    {"kind": "flower", "stages": ["·", "🌱", "🌷", "🌻", "🌼"]},
    {"kind": "cactus", "stages": ["·", "🌱", "🌵", "🌵"]},
    {"kind": "tree", "stages": ["·", "🌱", "🌿", "🌳", "🌳"]},
]

KIND_BY_NAME = {k["kind"]: k for k in KINDS}

WEATHERS = [
    ("☀️ sunny", 0),
    ("🌧️ rainy", 1),
    ("💨 windy", -1),
    ("☁️ cloudy", 0),
]


def load_garden():
    if GARDEN_FILE.exists():
        return json.loads(GARDEN_FILE.read_text(encoding="utf-8"))
    return {"step": 0, "plants": [], "log": []}


def save_garden(garden):
    GARDEN_FILE.write_text(json.dumps(garden, indent=2), encoding="utf-8")


def seedbank_path(name):
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", name):
        raise ValueError("seed names may only contain letters, digits, underscores, and hyphens")
    SEEDBANK_DIR.mkdir(exist_ok=True)
    return SEEDBANK_DIR / f"{name}.json"


def save_seed(name):
    src = load_garden()
    path = seedbank_path(name)
    path.write_text(json.dumps(src, indent=2), encoding="utf-8")
    return path


def load_seed(name):
    path = seedbank_path(name)
    if not path.exists():
        raise FileNotFoundError(f"no seed bank named {name!r}")
    return json.loads(path.read_text(encoding="utf-8"))


def emoji(plant):
    if plant.get("withered", False):
        return "💀"
    stages = plant["stages"]
    stage_index = min(plant["age"] // 3, len(stages) - 1)
    return stages[stage_index]


def season(step):
    return ["🌸 spring", "☀️ summer", "🍂 autumn", "❄️ winter"][(step - 1) % 4]


def render_html(garden):
    step = garden["step"]
    grid = [[None for _ in range(10)] for _ in range(5)]
    for plant in garden["plants"]:
        grid[plant["y"]][plant["x"]] = emoji(plant)

    rows_html = "\n".join(
        "<div class='garden-row'>"
        + "".join(f"<span class='garden-cell'>{cell or ' '}</span>" for cell in row)
        + "</div>"
        for row in grid
    )

    plants_html = "<ul class='plants'>\n" + "\n".join(
        f"<li>{emoji(p)} <strong>{p['kind']}</strong> — age {p['age']}, health {p['health']}/10"
        + (" <em>(withering)</em>" if p.get("withered") else "")
        + "</li>"
        for p in garden["plants"]
    ) + "\n</ul>"

    log_html = "<ul class='log'>\n" + "\n".join(
        f"<li>{entry}</li>" for entry in garden["log"][-10:]
    ) + "\n</ul>"

    latest = garden["log"][-1] if garden["log"] else ""
    meta = latest.split(" — ", 1)[1] if " — " in latest else ""

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>Terrarium Garden</title>
<link rel="stylesheet" href="style.css">
</head>
<body class="dark">
<nav>
  <a href="/">🏠 home</a>
  <a href="/journal">📓 journal</a>
  <a href="/grow">🌱 grow</a>
  <a href="/seedbank">🍃 seed bank</a>
</nav>
<h1>🌿 Terrarium Garden — Step {step}</h1>
<p class="meta">{meta}</p>
<div class="garden-bed">
{rows_html}
</div>
<h2>Plants</h2>
{plants_html}
<h2>🧑‍🌾 Tend the garden</h2>
<form method="post" action="/water" style="display:inline">
  <button type="submit">💧 water all plants</button>
</form>
<form method="post" action="/plant" style="margin-top:0.5em">
  <label>plant
    <select name="kind">
      <option value="moss">moss 🌿</option>
      <option value="fern">fern 🌴</option>
      <option value="flower">flower 🌼</option>
      <option value="cactus">cactus 🌵</option>
      <option value="tree">tree 🌳</option>
    </select>
  </label>
  at x <input name="x" type="number" min="0" max="9" value="0" required>
  y <input name="y" type="number" min="0" max="4" value="0" required>
  <button type="submit">🌱 plant</button>
</form>
<h2>Recent log</h2>
{log_html}
</body>
</html>
"""
    OUT_FILE.write_text(html, encoding="utf-8")


def tick(garden, water=False, plant_args=None):
    garden["step"] += 1
    step = garden["step"]
    notes = []

    # Prune plants that withered in the previous step.
    before = len(garden["plants"])
    garden["plants"] = [p for p in garden["plants"] if not p.get("withered", False)]
    pruned = before - len(garden["plants"])
    if pruned:
        notes.append(f"🍂 {pruned} plant(s) returned to soil")

    # Weather for this step.
    weather, weather_health = random.choice(WEATHERS)
    notes.append(f"{weather} {season(step)}")

    if water:
        watered = 0
        for plant in garden["plants"]:
            if plant["health"] < 10:
                plant["health"] = min(10, plant["health"] + 2)
                watered += 1
        notes.append(f"💧 watered {watered} thirsty plant(s)")

    if plant_args:
        kind_name, xs, ys = plant_args
        kind_name = kind_name.lower()
        if kind_name not in KIND_BY_NAME:
            raise ValueError(f"Unknown kind: {kind_name}. Known: {', '.join(KIND_BY_NAME)}")
        try:
            x, y = int(xs), int(ys)
        except ValueError:
            raise ValueError("X and Y must be integers.")
        if not (0 <= x <= 9 and 0 <= y <= 4):
            raise ValueError("Position must be inside the 10x5 grid (x 0-9, y 0-4).")
        if any(p["x"] == x and p["y"] == y for p in garden["plants"]):
            raise ValueError(f"There is already a plant at ({x},{y}).")
        template = KIND_BY_NAME[kind_name]
        garden["plants"].append({
            "kind": template["kind"],
            "stages": template["stages"],
            "age": 0,
            "health": random.randint(7, 10),
            "x": x,
            "y": y,
        })
        notes.append(f"🌱 planted {kind_name} at ({x},{y})")

    # Age existing plants and nudge health from weather.
    for plant in garden["plants"]:
        plant["age"] += 1
        plant["health"] = max(0, min(10, plant["health"] + weather_health + random.choice([-1, 0, 0, 1])))
        if plant["health"] == 0:
            plant["withered"] = True

    # Maybe a new seedling appears naturally.
    if not garden["plants"] or random.random() < 0.45:
        template = random.choice(KINDS)
        attempts = 0
        while attempts < 50:
            x, y = random.randint(0, 9), random.randint(0, 4)
            if not any(p["x"] == x and p["y"] == y for p in garden["plants"]):
                break
            attempts += 1
        garden["plants"].append({
            "kind": template["kind"],
            "stages": template["stages"],
            "age": 0,
            "health": random.randint(6, 10),
            "x": x,
            "y": y,
        })

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    log_entry = f"Step {step}: {len(garden['plants'])} plants — {now}"
    if notes:
        log_entry += " — " + "; ".join(notes)
    garden["log"].append(log_entry)

    render_html(garden)
    save_garden(garden)


def main():
    parser = argparse.ArgumentParser(description="Tiny generative terrarium garden")
    parser.add_argument("--water", action="store_true", help="water every plant (+1 health)")
    parser.add_argument("--plant", nargs=3, metavar=("KIND", "X", "Y"),
                        help="plant a seedling at the given grid position (0-9, 0-4)")
    parser.add_argument("--save", metavar="NAME", help="save the current garden to the seed bank")
    parser.add_argument("--load", metavar="NAME", help="restore a garden from the seed bank")
    args = parser.parse_args()

    try:
        if args.save:
            path = save_seed(args.save)
            print(f"💾 saved garden snapshot to {path.name}")
            return

        if args.load:
            garden = load_seed(args.load)
            save_garden(garden)
            render_html(garden)
            print(f"📂 loaded garden snapshot {args.load!r} — step {garden['step']}")
            return

        garden = load_garden()
        tick(garden, water=args.water, plant_args=args.plant)
        print(f"Garden step {garden['step']}: {len(garden['plants'])} plant(s). View rendered/garden.html")
    except (ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
