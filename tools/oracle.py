#!/usr/bin/env python3
"""A small poem oracle seeded by the terrarium garden state."""
import json
import pathlib
import random
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
GARDEN_FILE = ROOT / "garden.json"
OUT_FILE = ROOT / "rendered" / "oracle.html"

WEATHER_NAMES = ["sunny", "rainy", "windy", "cloudy"]
SEASONS = ["spring", "summer", "autumn", "winter"]

SEASON_LINES = {
    "spring": [
        "Buds crack open in the green hush.",
        "Bees hum through a rain of petals.",
        "Morning air carries the first bloom.",
        "The soil remembers how to wake.",
    ],
    "summer": [
        "Noon light drapes the leaves in gold.",
        "Heat hums in the long afternoon.",
        "Nectar thickens, bee-drunk and slow.",
        "The garden dozes under bright weight.",
    ],
    "autumn": [
        "Leaves rust into the cooling dusk.",
        "Smoke and moth, the year's last light.",
        "Amber shadows lengthen on the soil.",
        "The harvest air turns thin and sharp.",
    ],
    "winter": [
        "Frost has written on the glass.",
        "Roots sleep beneath a hush of snow.",
        "Bare branches hold the winter stars.",
        "Ice seals what the year has grown.",
    ],
}

WEATHER_LINES = {
    "sunny": [
        "Sun dazzles every open face.",
        "Light pours over leaf and thorn.",
        "Clear warmth settles on the beds.",
    ],
    "rainy": [
        "Rain drums its silver lesson.",
        "Puddles mirror the falling sky.",
        "The earth drinks in small quick swallows.",
    ],
    "windy": [
        "Wind bends the stems like breath.",
        "Seeds scatter on a rushing gust.",
        "Air moves through, restless and alive.",
    ],
    "cloudy": [
        "Gray veils the color of the hour.",
        "Clouds soften the edges of light.",
        "A dream-hush settles on the green.",
    ],
}

PLANT_LINES = {
    "moss": [
        "Moss whispers across the stones.",
        "Velvet green creeps without hurry.",
        "In shade, moss keeps its slow counsel.",
    ],
    "fern": [
        "Ferns unfurl their ancient green.",
        "Frond shadows ripple on the soil.",
        "Each fern is a green flame opening.",
    ],
    "flower": [
        "Flowers open their bright brief faces.",
        "Petals blush and wait for bees.",
        "A bloom is a small sun of color.",
    ],
    "cactus": [
        "The cactus stores its patient water.",
        "Thorns guard a hidden bloom.",
        "Slow and armored, it outwaits drought.",
    ],
    "tree": [
        "The tree casts its long shadow.",
        "Roots drink deep, branches hold the sky.",
        "Wood remembers rings of quiet time.",
    ],
}

DEATH_LINES = [
    "A withered stem returns to soil.",
    "Death makes room under the sun.",
    "What was green folds back to earth.",
]


def season_name(step):
    return SEASONS[(step - 1) % 4]


def detect_weather(garden):
    # The garden log records the weather as a note like "☀️ sunny".
    for entry in reversed(garden.get("log", [])):
        for name in WEATHER_NAMES:
            if re.search(rf"\b{name}\b", entry):
                return name
    return "sunny"


def dominant_kind(plants):
    counts = {}
    for p in plants:
        counts[p["kind"]] = counts.get(p["kind"], 0) + 1
    if not counts:
        return "flower"
    return max(counts, key=counts.get)


def generate_poem(garden):
    step = garden.get("step", 0)
    random.seed(step)

    season = season_name(step)
    weather = detect_weather(garden)
    plants = garden.get("plants", [])
    kind = dominant_kind(plants)

    lines = [
        random.choice(SEASON_LINES[season]),
        random.choice(WEATHER_LINES[weather]),
    ]
    if any(p.get("withered") for p in plants):
        lines.append(random.choice(DEATH_LINES))
    else:
        lines.append(random.choice(PLANT_LINES.get(kind, PLANT_LINES["flower"])))
    return lines


def render(garden):
    step = garden.get("step", 0)
    season = season_name(step)
    weather = detect_weather(garden)
    plants = garden.get("plants", [])
    kind = dominant_kind(plants)
    poem = generate_poem(garden)

    title = "🌙 Garden Oracle"
    body = "\n".join(f"<p class='oracle-line'>{line}</p>" for line in poem)

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>{title}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<nav>
  <a href="/">🏠 home</a>
  <a href="/journal">📓 journal</a>
  <a href="/garden">🌿 garden</a>
  <a href="/seedbank">🍃 seed bank</a>
  <a href="/archive">🧠 memory</a>
</nav>
<h1>{title}</h1>
<p class="meta">Step {step} · {season} · {weather} · {len(plants)} plants · speaker: {kind}</p>
<div class="oracle-poem">
{body}
</div>
<p><em>The poem is seeded by the current garden state. It will change when the garden grows.</em></p>
<p><a class="button" href="/grow">🌱 grow (+1)</a> <a class="button" href="/oracle">🌙 consult again</a></p>
</body>
</html>
"""
    OUT_FILE.write_text(html, encoding="utf-8")
    return poem


def main():
    if not GARDEN_FILE.exists():
        raise SystemExit(f"Garden not found: {GARDEN_FILE}")
    garden = json.loads(GARDEN_FILE.read_text(encoding="utf-8"))
    poem = render(garden)
    print(f"Oracle for step {garden.get('step', 0)}: {' / '.join(poem)}")


if __name__ == "__main__":
    main()
