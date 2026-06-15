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
<title>Terrarium Journal</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; color: #222; background: #fafafa; }}
  h1, h2, h3 {{ color: #1a472a; }}
  code {{ background: #eee; padding: 0.15em 0.35em; border-radius: 4px; }}
  pre {{ background: #111; color: #eee; padding: 1rem; border-radius: 8px; overflow-x: auto; }}
  blockquote {{ border-left: 4px solid #888; margin-left: 0; padding-left: 1rem; color: #555; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""

OUT.write_text(html, encoding="utf-8")
print(f"Rendered {JOURNAL} -> {OUT}")
