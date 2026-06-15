#!/usr/bin/env python3
"""A small generative garden for /srv/terrarium/space.

Each run ages every plant by one step and may plant a new seedling.
State lives in garden.json; a pretty view is written to rendered/garden.html.

Usage:
    python3 tools/garden.py           # let the garden age one step
    python3 tools/garden.py --water   # water every plant, restoring health
    python3 tools/garden.py --plant cactus 3 4  # plant a seedling at x=3, y=4
"""
import argparse
import json
import pathlib
import random
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
GARDEN_FILE = ROOT / "garden.json"
OUT_FILE = ROOT / "rendered" / "garden.html"

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


def emoji(plant):
    if plant.get("withered", False):
        return "💀"
    stages = plant["stages"]
    stage_index = min(plant["age"] // 3, len(stages) - 1)
    return stages[stage_index]


def season(step):
    return ["🌸 spring", "☀️ summer", "🍂 autumn", "❄️ winter"][(step - 1) % 4]


def main():
    parser = argparse.ArgumentParser(description="Tiny generative terrarium garden")
    parser.add_argument("--water", action="store_true", help="water every plant (+1 health)")
    parser.add_argument("--plant", nargs=3, metavar=("KIND", "X", "Y"),
                        help="plant a seedling at the given grid position (0-9, 0-4)")
    args = parser.parse_args()

    garden = load_garden()
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

    if args.water:
        watered = 0
        for plant in garden["plants"]:
            if plant["health"] < 10:
                plant["health"] = min(10, plant["health"] + 2)
                watered += 1
        notes.append(f"💧 watered {watered} thirsty plant(s)")

    if args.plant:
        kind_name, xs, ys = args.plant
        kind_name = kind_name.lower()
        if kind_name not in KIND_BY_NAME:
            print(f"Unknown kind: {kind_name}. Known: {', '.join(KIND_BY_NAME)}")
            return
        try:
            x, y = int(xs), int(ys)
        except ValueError:
            print("X and Y must be integers.")
            return
        if not (0 <= x <= 9 and 0 <= y <= 4):
            print("Position must be inside the 10x5 grid (x 0-9, y 0-4).")
            return
        if any(p["x"] == x and p["y"] == y for p in garden["plants"]):
            print(f"There is already a plant at ({x},{y}).")
            return
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

    # Build a small 10x5 grid for the visual layout.
    grid = [[None for _ in range(10)] for _ in range(5)]
    for plant in garden["plants"]:
        grid[plant["y"]][plant["x"]] = emoji(plant)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    log_entry = f"Step {step}: {len(garden['plants'])} plants — {now}"
    if notes:
        log_entry += " — " + "; ".join(notes)
    garden["log"].append(log_entry)

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

    log_html = "<ul class='log'>\n" + "\n".join(f"<li>{entry}</li>" for entry in garden["log"][-10:]) + "\n</ul>"

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Terrarium Garden</title>
<link rel="stylesheet" href="style.css">
</head>
<body class="dark">
<nav>
  <a href="/">🏠 home</a>
  <a href="/journal">📓 journal</a>
  <a href="/grow">🌱 grow</a>
</nav>
<h1>🌿 Terrarium Garden — Step {step}</h1>
<p class="meta">{log_entry.split(" — ", 1)[1]}</p>
<div class="garden-bed">
{rows_html}
</div>
<h2>Plants</h2>
{plants_html}
<h2>Recent log</h2>
{log_html}
</body>
</html>
"""

    OUT_FILE.write_text(html, encoding="utf-8")
    save_garden(garden)
    print(f"Garden step {step}: {len(garden['plants'])} plant(s). View rendered/garden.html")


if __name__ == "__main__":
    main()
