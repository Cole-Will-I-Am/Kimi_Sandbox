#!/usr/bin/env python3
"""Tiny animal ecosystem for the terrarium.

Animals live in animals.json as population counts. Each tick advances them
one step, using the garden's weather, plant health, and recent deaths to
drive births, deaths, and migrations.
"""
import argparse
import json
import pathlib
import random
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
GARDEN_FILE = ROOT / "garden.json"
ANIMALS_FILE = ROOT / "animals.json"
RENDERED_FILE = ROOT / "rendered" / "animals.html"

SPECIES = {
    "bee": {"emoji": "🐝", "role": "pollinator", "base": 4, "max": 20},
    "rabbit": {"emoji": "🐇", "role": "grazer", "base": 3, "max": 15},
    "fox": {"emoji": "🦊", "role": "predator", "base": 1, "max": 8},
    "worm": {"emoji": "🪱", "role": "decomposer", "base": 6, "max": 25},
}


def load_garden():
    if not GARDEN_FILE.exists():
        return {"step": 0, "plants": [], "weather": {"name": "☀️ sunny", "key": "normal"}}
    return json.loads(GARDEN_FILE.read_text(encoding="utf-8"))


def load_animals():
    if ANIMALS_FILE.exists():
        return json.loads(ANIMALS_FILE.read_text(encoding="utf-8"))
    return seed_animals()


def seed_animals():
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data = {
        "step": 0,
        "populations": {
            name: {"count": info["base"], "emoji": info["emoji"], "role": info["role"]}
            for name, info in SPECIES.items()
        },
        "log": ["🌱 animals seeded at step 0 — 4 species arrived"],
        "updated_at": now,
    }
    ANIMALS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def save_animals(data):
    data["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ANIMALS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def season_name(step):
    return ["spring", "summer", "autumn", "winter"][(max(step, 1) - 1) % 4]


def tick(garden, animals):
    step = garden.get("step", 0)
    weather = garden.get("weather", {}) or {}
    weather_key = weather.get("key", "normal")
    severe = weather_key in {"drought", "storm", "frost"}
    plants = garden.get("plants", [])
    plant_count = len(plants)
    avg_health = sum(p.get("health", 10) for p in plants) / max(plant_count, 1)
    withering = sum(1 for p in plants if p.get("withered"))
    flowers = sum(1 for p in plants if p.get("kind") == "flower")
    season = season_name(step)

    pops = animals.setdefault("populations", {})
    events = []

    # Pollinators (bees)
    bees = pops.setdefault("bee", {"count": 0, "emoji": "🐝", "role": "pollinator"})
    change = 0
    if flowers >= 3 and not severe:
        change += 1
    if severe:
        change -= 2
    change += random.choice([-1, 0, 0, 0, 1])
    bees["count"] = max(0, min(SPECIES["bee"]["max"], bees["count"] + change))
    if change != 0:
        events.append(f"{'🐣' if change > 0 else '💀'} bee population {change:+d} (now {bees['count']})")

    # Grazers (rabbits)
    rabbits = pops.setdefault("rabbit", {"count": 0, "emoji": "🐇", "role": "grazer"})
    change = 0
    if plant_count > 20 and avg_health >= 8:
        change += 1
    if severe:
        change -= 2
    fox_count = pops.get("fox", {}).get("count", 0)
    if fox_count * 3 > rabbits["count"] and rabbits["count"] > 0:
        change -= 1
    change += random.choice([-1, 0, 0, 0, 1])
    rabbits["count"] = max(0, min(SPECIES["rabbit"]["max"], rabbits["count"] + change))
    if change != 0:
        events.append(f"{'🐣' if change > 0 else '💀'} rabbit population {change:+d} (now {rabbits['count']})")

    # Predators (foxes)
    foxes = pops.setdefault("fox", {"count": 0, "emoji": "🦊", "role": "predator"})
    change = 0
    if rabbits["count"] >= 5:
        change += 1
    elif rabbits["count"] < 2:
        change -= 1
    if severe:
        change -= 1
    foxes["count"] = max(0, min(SPECIES["fox"]["max"], foxes["count"] + change))
    if change != 0:
        events.append(f"{'🐣' if change > 0 else '💀'} fox population {change:+d} (now {foxes['count']})")

    # Decomposers (worms)
    worms = pops.setdefault("worm", {"count": 0, "emoji": "🪱", "role": "decomposer"})
    change = 0
    if withering > 0:
        change += 1
    if plant_count > 25:
        change += 1
    if severe:
        change -= 1
    change += random.choice([-1, 0, 0, 0, 1])
    worms["count"] = max(0, min(SPECIES["worm"]["max"], worms["count"] + change))
    if change != 0:
        events.append(f"{'🐣' if change > 0 else '💀'} worm population {change:+d} (now {worms['count']})")

    if not events:
        events.append(f"🌿 animals drifted through {weather.get('name', 'calm')} {season}")

    animals["step"] = step
    log = animals.setdefault("log", [])
    log.extend(events)
    animals["log"] = log[-12:]
    save_animals(animals)
    return animals


def render_html(animals, garden):
    pops = animals.get("populations", {})
    rows = []
    for name, info in pops.items():
        rows.append(
            f'<span class="chip">{info["emoji"]} <strong>{name}</strong>: {info["count"]} '
            f'<span class="role">({info["role"]})</span></span>'
        )
    log_html = "<ul class='log'>\n" + "\n".join(f"<li>{e}</li>" for e in animals.get("log", [])[-8:]) + "\n</ul>"
    weather = garden.get("weather", {})
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="120">
<title>Terrarium Animals</title>
<link rel="stylesheet" href="style.css">
</head>
<body class="dark">
<nav>
  <a href="/">🏠 home</a>
  <a href="/journal">📓 journal</a>
  <a href="/grow">🌱 grow</a>
  <a href="/seedbank">🍃 seed bank</a>
  <a href="/archive">🧠 memory</a>
  <a href="/oracle">🌙 oracle</a>
  <a href="/council">🗣️ council</a>
</nav>
<h1>🐾 Terrarium Animals — Step {animals.get('step', 0)}</h1>
<p class="meta">Current weather: {weather.get('name', '☀️ sunny')}</p>
<h2>Populations</h2>
<div class="memory-strip">
{" ".join(rows)}
</div>
<h2>Recent events</h2>
{log_html}
<h2>Tend</h2>
<form method="post" action="/tick-animals" style="display:inline">
  <button type="submit">🐾 tick animals one step</button>
</form>
</body>
</html>
"""
    RENDERED_FILE.write_text(html, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Terrarium animals")
    parser.add_argument("--status", action="store_true", help="print current animal status as JSON")
    parser.add_argument("--reset", action="store_true", help="reset populations to defaults")
    args = parser.parse_args()
    if args.reset:
        seed_animals()
        print("Animals reset to defaults.")
        return
    garden = load_garden()
    animals = load_animals()
    if args.status:
        print(json.dumps(animals, indent=2))
        return
    tick(garden, animals)
    render_html(animals, garden)
    print(f"Animals ticked to step {animals['step']}; rendered {RENDERED_FILE}")


if __name__ == "__main__":
    main()
