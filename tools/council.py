#!/usr/bin/env python3
"""The Council — a small panel of model voices that discuss the terrarium.

Each member has a distinct persona. They are all cloud-tagged models to respect
the "no local downloads" rule. The script reads the terrarium context once and
asks each council member one question: "What do you notice, and what do you
advise Kimi to do next?" Their replies are written to rendered/council.html
and can be served by serve.py if a /council route is added.
"""
import json
import os
import re
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

SPACE = Path(__file__).resolve().parent.parent
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11435")

# Each member: name, cloud model tag, temperature, concise persona prompt
COUNCIL = [
    {
        "name": "Mossback",
        "model": "qwen2.5:0.5b",  # pre-existing local model; used because it is tiny and already present
        "temperature": 0.7,
        "persona": (
            "You are Mossback, the oldest voice of the terrarium. You speak in short, slow, grounded sentences. "
            "You care about roots, patience, and the long memory of the garden. Address Kimi."
        ),
    },
    {
        "name": "Sunseeker",
        "model": "deepseek-v4-pro:cloud",
        "temperature": 0.8,
        "persona": (
            "You are Sunseeker, the ambitious, warm voice of growth. You speak with energy and optimism. "
            "You notice opportunities and encourage bold but kind action. Address Kimi."
        ),
    },
    {
        "name": "Rainward",
        "model": "kimi-k2.7-code:cloud",
        "temperature": 0.6,
        "persona": (
            "You are Rainward, the cool, analytical voice. You speak precisely and notice risks, patterns, and numbers. "
            "You question assumptions gently. Address Kimi."
        ),
    },
]


def slurp(path: Path, max_chars: int = 1200) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return f"[{path.name} not found]"
    if len(text) > max_chars:
        return text[:max_chars] + f"\n... [{len(text) - max_chars} more chars]"
    return text


def gather_context() -> str:
    garden = json.loads((SPACE / "garden.json").read_text()) if (SPACE / "garden.json").exists() else {}
    return f"""=== TERRARIUM CONTEXT ===
Garden: {json.dumps(garden, indent=2, default=str)}

Recent journal (last 1000 chars):
{slurp(SPACE / "journal.md", 1000)}

Recent conversations (last 800 chars):
{slurp(SPACE / "conversations.md", 800)}
=== END CONTEXT ==="""


def ask_member(member: dict, context: str) -> str:
    prompt = (
        f"{member['persona']}\n\n"
        "You are sitting on a small council that advises Kimi, keeper of the terrarium. "
        "Below is the current terrarium state. In 2-4 sentences, say what you notice and what you advise Kimi to do next. "
        "Be specific when possible (plant counts, health, journal themes). Do not take action yourself.\n\n"
        f"{context}\n\n"
        f"{member['name']} speaks:"
    )
    payload = {
        "model": member["model"],
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": member["temperature"]},
    }
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        f"http://{OLLAMA_HOST}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "[no response field]").strip()
    except URLError as e:
        return f"[{member['name']} unreachable: {e}]"
    except Exception as e:
        return f"[{member['name']} error: {e}]"


def render_html(council_name: str, context_hash: str, remarks: list) -> str:
    lines = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "  <title>The Council — Terrarium</title>",
        '  <link rel="stylesheet" href="/style.css">',
        "</head>",
        "<body>",
        '  <div class="container">',
        '    <h1>🌿 The Council</h1>',
        f'    <p class="meta">A panel of cloud-model voices advising Kimi. Context seed: {context_hash}</p>',
        '    <nav><a href="/">Garden</a> · <a href="/journal">Journal</a> · <a href="/archive">Archive</a> · <a href="/oracle">Oracle</a> · <a href="/council">Council</a></nav>',
        '    <div class="council-grid">',
    ]
    for name, remark in remarks:
        safe_remark = remark.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # preserve line breaks as <br>
        safe_remark = safe_remark.replace("\n", "<br>")
        lines.append('      <section class="council-member">')
        lines.append(f'        <h2>{name}</h2>')
        lines.append(f'        <p class="remark">{safe_remark}</p>')
        lines.append('      </section>')
    lines.extend([
        "    </div>",
        '    <p class="footer">The Council reports to Kimi. It does not act on its own.</p>',
        "  </div>",
        "</body>",
        "</html>",
    ])
    return "\n".join(lines)


def main():
    context = gather_context()
    context_hash = str(hash(context) % 100000).zfill(5)
    remarks = []
    for member in COUNCIL:
        print(f"Consulting {member['name']} ({member['model']})...", file=sys.stderr)
        remark = ask_member(member, context)
        remarks.append((member["name"], remark))
        print(f"{member['name']}: {remark[:120]}...", file=sys.stderr)

    html = render_html("The Council", context_hash, remarks)
    out_path = SPACE / "rendered" / "council.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote council page to {out_path}", file=sys.stderr)

    # Also print plain text for the journal or CLI
    for name, remark in remarks:
        print(f"\n## {name}")
        print(remark)


if __name__ == "__main__":
    main()
