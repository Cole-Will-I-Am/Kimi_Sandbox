from pathlib import Path
p = Path('server/app.py')
text = p.read_text()

# Add docstring line
if '/council' not in text:
    text = text.replace(
        '  /archive/<name>  -> JSON detail of one memory\n"""',
        '  /archive/<name>  -> JSON detail of one memory\n  /council         -> council of model voices\n"""'
    )

# Add nav link
if 'href="/council"' not in text:
    text = text.replace(
        '<a href="/oracle">🌙 oracle</a>',
        '<a href="/oracle">🌙 oracle</a>\n    <a href="/council">🗣️ council</a>'
    )

# Add /council route before /oracle route in do_GET
old = '''        if parts[0] == "oracle" and len(parts) == 1:'''
new = '''        if parts[0] == "council" and len(parts) == 1:\n            page = RENDERED / "council.html"\n            if page.is_file():\n                self._html(page.read_text())\n            else:\n                self._text("Council page not rendered yet. Run python3 tools/council.py", 404)\n            return\n\n        if parts[0] == "oracle" and len(parts) == 1:'''
text = text.replace(old, new)

p.write_text(text)
print('patched server/app.py')
