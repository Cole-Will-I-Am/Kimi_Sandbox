#!/usr/bin/env python3
"""Terrarium Steward — co-manager status report.

Reads the current terrarium state, sends a structured context prompt to the
local terrarium-steward model, and prints a status report.
"""
import json
import os
import sys
import textwrap
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError


SPACE = Path(__file__).resolve().parent.parent
MODEL = os.environ.get("STEWARD_MODEL", "terrarium-steward:latest")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11435")


def slurp(path: Path, max_chars: int = 4000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return f"[{path.name} not found]"
    if len(text) > max_chars:
        return text[:max_chars] + f"\n... [{len(text) - max_chars} more chars]"
    return text


def gather_context() -> str:
    garden = json.loads((SPACE / "garden.json").read_text()) if (SPACE / "garden.json").exists() else {}

    lines = [
        "=== TERRARIUM CONTEXT ===",
        "",
        "--- garden.json ---",
        json.dumps(garden, indent=2, default=str),
        "",
        "--- server.log (recent) ---",
        slurp(SPACE / "server.log", 1200),
        "",
        "--- journal.md (last 2000 chars) ---",
        slurp(SPACE / "journal.md", 2000),
        "",
        "--- conversations.md (last 1200 chars) ---",
        slurp(SPACE / "conversations.md", 1200),
        "",
        "--- file inventory ---",
    ]
    for child in sorted(SPACE.iterdir()):
        marker = "d" if child.is_dir() else "f"
        lines.append(f"{marker} {child.name}")
    lines.append("")
    lines.append("=== END CONTEXT ===")
    return "\n".join(lines)


def ask_steward(context: str) -> str:
    payload = {
        "model": MODEL,
        "prompt": (
            "You are the Terrarium Steward reporting to Kimi.\n\n"
            "Below is the current state of the terrarium. Please produce your status report:\n"
            "1. Brief State Summary\n"
            "2. What's Going Well\n"
            "3. Concerns or Drift\n"
            "4. Top 3 Recommended Actions for the next waking\n"
            "5. Closing line to Kimi\n\n"
            f"{context}\n\n"
            "Steward's report:"
        ),
        "stream": False,
        "options": {"temperature": 0.6},
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
            return result.get("response", "[no response field]")
    except URLError as e:
        return f"[Steward unreachable: {e}]"
    except Exception as e:
        return f"[Steward error: {e}]"


def main():
    print(f"Consulting steward model '{MODEL}' at {OLLAMA_HOST}...")
    print()
    context = gather_context()
    report = ask_steward(context)
    print(report)


if __name__ == "__main__":
    main()
