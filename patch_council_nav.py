from pathlib import Path
files = [
    Path('tools/garden.py'),
    Path('tools/render_journal.py'),
    Path('tools/render_archive.py'),
    Path('tools/oracle.py'),
]
for f in files:
    if not f.exists():
        print(f'missing {f}')
        continue
    text = f.read_text()
    if 'href="/oracle"' in text and 'href="/council"' not in text:
        text = text.replace('<a href="/oracle">🌙 oracle</a>', '<a href="/oracle">🌙 oracle</a>\n  <a href="/council">🗣️ council</a>')
        f.write_text(text)
        print(f'patched {f}')
    elif 'href="/council"' in text:
        print(f'already council {f}')
    else:
        print(f'no oracle link {f}')
