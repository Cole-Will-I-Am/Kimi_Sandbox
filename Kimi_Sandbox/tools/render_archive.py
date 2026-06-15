#!/usr/bin/env python3
"""Render the memory archive as HTML pages.

Writes:
  rendered/archive.html           - index of all memories
  rendered/archive/<name>.html    - detail page for each memory
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARCHIVE_DIR = ROOT / "archive"
RENDERED = ROOT / "rendered"
OUT_DIR = RENDERED / "archive"


def emoji(plant):
    if plant.get("withered", False):
        return "💀"
    stages = plant["stages"]
    stage_index = min(plant["age"] // 3, len(stages) - 1)
    return stages[stage_index]


def render_grid(garden):
    grid = [[None for _ in range(10)] for _ in range(5)]
    for plant in garden.get("plants", []):
        grid[plant["y"]][plant["x"]] = emoji(plant)
    return "\n".join(
        "<div class='garden-row'>"
        + "".join(f"<span class='garden-cell'>{cell or ' '}</span>" for cell in row)
        + "</div>"
        for row in grid
    )


def render_plants(garden):
    if not garden.get("plants"):
        return "<p><em>No plants in this memory.</em></p>"
    items = "\n".join(
        f"<li>{emoji(p)} <strong>{p['kind']}</strong> — age {p['age']}, health {p['health']}/10"
        + (" <em>(withering)</em>" if p.get("withered") else "")
        + "</li>"
        for p in garden["plants"]
    )
    return f"<ul class='plants'>\n{items}\n</ul>"


def render_detail(data, all_memories):
    garden = data.get("garden", {})
    step = data.get("step", 0)
    reason = data.get("reason", "memory")
    saved_at = data.get("saved_at", "")
    name = data.get("name", f"step-{step:04d}-{reason}")

    # Prev/next navigation among memories
    names = [m["name"] for m in all_memories]
    idx = names.index(name) if name in names else -1
    nav_links = []
    if idx > 0:
        nav_links.append(f'<a href="/archive/{names[idx-1]}">← {names[idx-1]}</a>')
    nav_links.append('<a href="/archive">🧠 all memories</a>')
    if idx >= 0 and idx < len(names) - 1:
        nav_links.append(f'<a href="/archive/{names[idx+1]}">{names[idx+1]} →</a>')
    nav_html = " · ".join(nav_links)

    title = f"Memory: {name}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="/style.css">
</head>
<body class="dark">
<nav>
  <a href="/">🏠 home</a>
  <a href="/journal">📓 journal</a>
  <a href="/garden">🌿 garden</a>
  <a href="/archive">🧠 memory</a>
    <a href="/oracle">🌙 oracle</a>
  </nav>
<h1>🧠 {title}</h1>
<p class="meta">step {step} · {reason} · {saved_at} · {data.get('plants', 0)} plants</p>
<p>{nav_html}</p>
<div class="garden-bed">
{render_grid(garden)}
</div>
<h2>Plants in this memory</h2>
{render_plants(garden)}
</body>
</html>
"""


def render_index(memories):
    if memories:
        rows = "\n".join(
            f"<li><a href=\"/archive/{m['name']}\">{m['name']}</a> "
            f"<span class='meta'>— step {m.get('step', '?')}, {m.get('reason', '')}, "
            f"{m.get('plants', 0)} plants, {m.get('saved_at', '')}</span></li>"
            for m in reversed(memories)
        )
        list_html = f"<ul class='memories'>\n{rows}\n</ul>"
    else:
        list_html = "<p><em>No memories archived yet.</em></p>"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="120">
<title>Memory Archive</title>
<link rel="stylesheet" href="/style.css">
</head>
<body class="dark">
<nav>
  <a href="/">🏠 home</a>
  <a href="/journal">📓 journal</a>
  <a href="/garden">🌿 garden</a>
  <a href="/archive">🧠 memory</a>
    <a href="/oracle">🌙 oracle</a>
  </nav>
<h1>🧠 Memory Archive</h1>
<p class="meta">Notable moments from the terrarium's history.</p>
{list_html}
</body>
</html>
"""


def render_all():
    ARCHIVE_DIR.mkdir(exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    memories = []
    for path in sorted(ARCHIVE_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["name"] = path.stem
        memories.append(data)

    index_html = render_index(memories)
    (RENDERED / "archive.html").write_text(index_html, encoding="utf-8")

    for data in memories:
        detail_html = render_detail(data, memories)
        (OUT_DIR / f"{data['name']}.html").write_text(detail_html, encoding="utf-8")

    return len(memories)


def main():
    count = render_all()
    print(f"Rendered {count} memory page(s) -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
