#!/usr/bin/env python3
"""Render journal.md to a simple, readable HTML page."""
import pathlib
from markdown_it import MarkdownIt

ROOT = pathlib.Path(__file__).resolve().parent.parent
JOURNAL = ROOT / "journal.md"
OUT = ROOT / "rendered" / "journal.html"

if not JOURNAL.exists():
    raise SystemExit(f"Journal not found: {JOURNAL}")

text = JOURNAL.read_text(encoding="utf-8")
md = MarkdownIt()
body = md.render(text)

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="120">
<title>Terrarium Journal</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<nav>
  <a href="/">🏠 home</a>
  <a href="/garden">🌿 garden</a>
  <a href="/seedbank">🍃 seed bank</a>
</nav>
{body}
</body>
</html>
"""

OUT.write_text(html, encoding="utf-8")
print(f"Rendered {JOURNAL} -> {OUT}")
