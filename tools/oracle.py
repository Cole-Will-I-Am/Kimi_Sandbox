#!/usr/bin/env python3
"""A small poem oracle seeded by the terrarium garden state.

Supports two modes:
- free: three-line free verse (legacy)
- haiku: 5-7-5 syllable poems composed from counted phrase banks
"""
import json
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parent.parent
GARDEN_FILE = ROOT / "garden.json"
OUT_FILE = ROOT / "rendered" / "oracle.html"

WEATHER_NAMES = ["sunny", "rainy", "windy", "cloudy"]
SEASONS = ["spring", "summer", "autumn", "winter"]

# ---------------------------------------------------------------------------
# Free-verse phrase banks (legacy)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Haiku phrase banks: each phrase is (text, syllables)
# Themes: season, weather, plant, death
# ---------------------------------------------------------------------------
HAiku_FIVE = {
    "spring": [
        ("green buds break open", 5),
        ("bees hum in new rain", 5),
        ("first bloom, soft and bright", 5),
        ("the soil wakes, warm, slow", 5),
        ("petals fall like snow", 5),
        ("new seeds wait to rise", 5),
        ("dawn air smells of green", 5),
        ("soft rain, sweet and bright", 5),
    ],
    "summer": [
        ("long noon, heavy gold", 5),
        ("bees drone, thick and slow", 5),
        ("leaves hold the bright sky", 5),
        ("heat hums in green shade", 5),
        ("nectar drips so slow", 5),
        ("white moths seek the bloom", 5),
        ("sun bakes the dark soil", 5),
        ("long shadows stretch out", 5),
    ],
    "autumn": [
        ("leaves rust, then let go", 5),
        ("cold dusk, thin and sharp", 5),
        ("moth light, amber, brief", 5),
        ("harvest air turns cool", 5),
        ("smoke threads through bare trees", 5),
        ("red leaves fall like fire", 5),
        ("the year sheds its green", 5),
        ("soft gold turns to brown", 5),
    ],
    "winter": [
        ("frost writes on the glass", 5),
        ("roots sleep under snow", 5),
        ("bare boughs hold the stars", 5),
        ("ice seals the still pond", 5),
        ("white hush, deep and long", 5),
        ("cold air bites the cheek", 5),
        ("dark earth dreams of spring", 5),
        ("still pond, white and hard", 5),
    ],
    "sunny": [
        ("sun opens each face", 5),
        ("bright warmth on the beds", 5),
        ("clear light, leaf and thorn", 5),
        ("gold pours on green leaves", 5),
        ("noon hums, soft and bright", 5),
    ],
    "rainy": [
        ("rain drums its silver", 5),
        ("soft puddles hold sky", 5),
        ("earth drinks, quick and deep", 5),
        ("wet leaves bow and drip", 5),
        ("gray clouds weep, slow, soft", 5),
    ],
    "windy": [
        ("wind bends the green stems", 5),
        ("seeds fly, wild and free", 5),
        ("air moves, restless, bright", 5),
        ("dry leaves race like birds", 5),
        ("branches bow and sigh", 5),
    ],
    "cloudy": [
        ("gray veils the bright hour", 5),
        ("clouds soften all light", 5),
        ("green dreams under gray", 5),
        ("no sun, no shade, hush", 5),
        ("dusk comes soft and slow", 5),
    ],
    "moss": [
        ("moss creeps on cold stone", 5),
        ("soft green, slow and low", 5),
        ("velvet keeps the shade", 5),
        ("moss holds the damp hush", 5),
        ("green threads, fine and still", 5),
    ],
    "fern": [
        ("ferns unfold, green flames", 5),
        ("frond shadows ripple", 5),
        ("old green, young and bright", 5),
        ("fiddleheads uncurl", 5),
        ("shade leaves lift and sway", 5),
    ],
    "flower": [
        ("bright blooms face the sun", 5),
        ("petals blush for bees", 5),
        ("small suns, brief and sweet", 5),
        ("one bud breaks to red", 5),
        ("scent drifts, soft, unseen", 5),
    ],
    "cactus": [
        ("cactus stores slow rain", 5),
        ("thorns guard hidden bloom", 5),
        ("patient, armed, and still", 5),
        ("thick green holds the drought", 5),
        ("spines watch the bright sun", 5),
    ],
    "tree": [
        ("tree casts a long shade", 5),
        ("roots drink, boughs hold sky", 5),
        ("wood rings quiet time", 5),
        ("one trunk, slow and old", 5),
        ("leaves murmur, soft, high", 5),
    ],
    "death": [
        ("withered stem, dark soil", 5),
        ("death makes room for green", 5),
        ("what was green folds back", 5),
        ("brown leaves, dry and still", 5),
        ("life sleeps in the rot", 5),
    ],
}

HAiku_SEVEN = {
    "spring": [
        ("the soil remembers waking", 7),
        ("morning air carries first bloom", 7),
        ("petal rain, soft and constant", 7),
        ("new green pushes through old mulch", 7),
        ("small buds swell with waited rain", 7),
        ("the garden wakes, green and slow", 7),
    ],
    "summer": [
        ("noon light drapes the leaves in gold", 7),
        ("the garden dozes, warm, bright", 7),
        ("nectar thickens, bee-drunk, slow", 7),
        ("long shadows stretch across the beds", 7),
        ("white moths drift from bloom to bloom", 7),
        ("the hot air hums with insect song", 7),
    ],
    "autumn": [
        ("leaves rust into cooling dusk", 7),
        ("amber shadows lengthen, thin", 7),
        ("the year's last light turns sharp, clear", 7),
        ("smoke and moth, the harvest air", 7),
        ("red leaves fall like small bright fires", 7),
        ("cold dusk comes early, soft, gray", 7),
    ],
    "winter": [
        ("roots sleep beneath a hush of snow", 7),
        ("ice seals what the year has grown", 7),
        ("bare branches hold the winter stars", 7),
        ("frost writes white script on the glass", 7),
        ("dark earth dreams beneath the still pond", 7),
        ("the cold air bites, sharp and clean", 7),
    ],
    "sunny": [
        ("sun dazzles each open face", 7),
        ("clear warmth settles on the beds", 7),
        ("light pours over leaf and thorn", 7),
        ("gold light fills green waiting cups", 7),
        ("noon hums bright, soft, without end", 7),
    ],
    "rainy": [
        ("rain drums its silver lesson", 7),
        ("puddles mirror the gray sky", 7),
        ("earth drinks in small, quick swallows", 7),
        ("wet leaves bow beneath each clear drop", 7),
        ("gray clouds weep on the green beds", 7),
    ],
    "windy": [
        ("wind bends stems like a slow breath", 7),
        ("seeds scatter on a rushing gust", 7),
        ("air moves, restless and alive", 7),
        ("dry leaves race like small brown birds", 7),
        ("branches bow and sigh, then lift", 7),
    ],
    "cloudy": [
        ("gray veils the color of dusk", 7),
        ("clouds soften the edges of light", 7),
        ("dream-hush settles on the green", 7),
        ("no sun, no shade, just soft hush", 7),
        ("dusk comes soft and slow under", 7),
    ],
    "moss": [
        ("moss whispers across the cold stones", 7),
        ("velvet green creeps without pause", 7),
        ("in shade, moss keeps its slow counsel", 7),
        ("moss holds damp hush of the stones", 7),
        ("green threads, fine, still, wait for rain", 7),
    ],
    "fern": [
        ("ferns unfurl their ancient green", 7),
        ("frond shadows ripple on soil", 7),
        ("each fern is a small green flame", 7),
        ("fiddleheads uncurl in soft shade", 7),
        ("shade leaves lift and sway so fine", 7),
    ],
    "flower": [
        ("small blooms open their bright faces", 7),
        ("petals blush and wait for the bees", 7),
        ("a bloom is a small red sun", 7),
        ("one bud breaks to red in sun", 7),
        ("scent drifts, soft, unseen, sweet, brief", 7),
    ],
    "cactus": [
        ("cactus holds its cool water", 7),
        ("thorns guard hidden, waiting bloom", 7),
        ("slow, armored, it outwaits drought", 7),
        ("thick green holds drought in its flesh", 7),
        ("spines watch the bright sun, slow, armed", 7),
    ],
    "tree": [
        ("tree casts its long, slow shadow", 7),
        ("roots drink deep, branches hold sky", 7),
        ("wood remembers quiet time", 7),
        ("one trunk, slow and old, keeps wind", 7),
        ("leaves murmur, high in the blue", 7),
    ],
    "death": [
        ("a withered stem returns to soil", 7),
        ("death makes room under bright sun", 7),
        ("what was green folds back to earth", 7),
        ("brown leaves dry, still, hold their breath", 7),
        ("life sleeps in the rot, waiting, warm", 7),
    ],
}


def season_name(step):
    return SEASONS[(step - 1) % 4]


def detect_weather(garden):
    import re
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


def generate_free_poem(garden):
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


def _choose_line(target, theme, bank, fallback_bank):
    """Pick a phrase combination summing to `target` syllables.

    Try the requested theme first, then fall back to the whole bank.
    Returns a (line_text, syllables) tuple or None.
    """
    candidates = bank.get(theme, [])
    for text, syllables in candidates:
        if syllables == target:
            return text, syllables
    # If no exact single phrase, try two phrases from the same theme.
    for t1, s1 in candidates:
        for t2, s2 in candidates:
            if s1 + s2 == target:
                return f"{t1}, {t2}", target
    # Fallback: scan the entire bank.
    all_phrases = [p for phrases in bank.values() for p in phrases]
    for text, syllables in all_phrases:
        if syllables == target:
            return text, syllables
    for t1, s1 in all_phrases:
        for t2, s2 in all_phrases:
            if s1 + s2 == target:
                return f"{t1}, {t2}", target
    return None


def generate_haiku(garden):
    """Compose a deterministic 5-7-5 haiku from the garden state."""
    step = garden.get("step", 0)
    random.seed(step)

    season = season_name(step)
    weather = detect_weather(garden)
    plants = garden.get("plants", [])
    kind = dominant_kind(plants)
    theme3 = "death" if any(p.get("withered") for p in plants) else kind

    # Build line 1 (5) from season + weather mix.
    line1 = _choose_line(5, season, HAiku_FIVE, HAiku_FIVE)
    if line1 is None:
        line1 = _choose_line(5, weather, HAiku_FIVE, HAiku_FIVE)
    if line1 is None:
        line1 = ("the garden breathes", 5)

    # Build line 2 (7) from weather + plant mix.
    line2 = _choose_line(7, weather, HAiku_SEVEN, HAiku_SEVEN)
    if line2 is None:
        line2 = _choose_line(7, kind, HAiku_SEVEN, HAiku_SEVEN)
    if line2 is None:
        line2 = ("the slow green world turns", 7)

    # Build line 3 (5) from plant/death + season mix.
    line3 = _choose_line(5, theme3, HAiku_FIVE, HAiku_FIVE)
    if line3 is None:
        line3 = _choose_line(5, season, HAiku_FIVE, HAiku_FIVE)
    if line3 is None:
        line3 = ("life waits in the soil", 5)

    return [line1[0], line2[0], line3[0]]


def generate_poem(garden, mode="haiku"):
    if mode == "free":
        return generate_free_poem(garden)
    return generate_haiku(garden)


LOG_FILE = ROOT / "oracle_log.jsonl"


def _log_poem(poem, mode, step):
    """Append a DISTINCT poem to oracle_log.jsonl (skips duplicates of the last
    ~60, so page refreshes don't spam). A root-side shipper publishes new ones
    to the monitor's Oracle gallery."""
    try:
        joined = " / ".join(poem)
        if LOG_FILE.exists():
            recent = [ln for ln in LOG_FILE.read_text(encoding="utf-8").splitlines() if ln.strip()][-60:]
            for ln in recent:
                try:
                    if " / ".join(json.loads(ln).get("lines", [])) == joined:
                        return  # already have this exact poem recently
                except json.JSONDecodeError:
                    continue
        import datetime
        entry = {
            "ts": datetime.datetime.now(datetime.UTC).isoformat(),
            "mode": mode,
            "garden_step": step,
            "lines": list(poem),
        }
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def render(garden, mode="haiku"):
    step = garden.get("step", 0)
    season = season_name(step)
    weather = detect_weather(garden)
    plants = garden.get("plants", [])
    kind = dominant_kind(plants)
    poem = generate_poem(garden, mode=mode)
    form_label = "haiku" if mode == "haiku" else "free verse"

    title = "🌙 Garden Oracle"
    body = "\n".join(f"<p class='oracle-line'>{line}</p>" for line in poem)

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="120">
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
  <a href="/council">🗣️ council</a>
</nav>
<h1>{title}</h1>
<p class="meta">Step {step} · {season} · {weather} · {len(plants)} plants · speaker: {kind} · form: {form_label}</p>
<div class="oracle-poem {mode}">
{body}
</div>
<p><em>The poem is seeded by the current garden state. It will change when the garden grows.</em></p>
<p>
  <a class="button" href="/grow">🌱 grow (+1)</a>
  <a class="button" href="/oracle">🌙 consult again</a>
  <a class="button" href="/oracle?mode=haiku">🍃 haiku</a>
  <a class="button" href="/oracle?mode=free">🌾 free verse</a>
</p>
</body>
</html>
"""
    OUT_FILE.write_text(html, encoding="utf-8")
    _log_poem(poem, mode, step)
    return poem





def main():
    import argparse
    parser = argparse.ArgumentParser(description="Garden poem oracle")
    parser.add_argument("--mode", choices=["haiku", "free"], default="haiku",
                        help="poem form to generate (default: haiku)")
    args = parser.parse_args()

    if not GARDEN_FILE.exists():
        raise SystemExit(f"Garden not found: {GARDEN_FILE}")
    garden = json.loads(GARDEN_FILE.read_text(encoding="utf-8"))
    poem = render(garden, mode=args.mode)
    print(f"Oracle for step {garden.get('step', 0)}: {' / '.join(poem)}")


if __name__ == "__main__":
    main()
