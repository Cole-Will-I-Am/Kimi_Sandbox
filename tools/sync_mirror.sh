#!/usr/bin/env bash
set -euo pipefail
# sync_mirror.sh — copy /srv/terrarium/space into Kimi_Sandbox, commit, and push.

SOURCE="/srv/terrarium/space"
MIRROR="${SOURCE}/Kimi_Sandbox"

if [[ ! -d "$MIRROR/.git" ]]; then
    echo "Error: mirror directory is not a git repository: $MIRROR"
    exit 1
fi

# Mirror live state. Exclude the mirror itself to avoid nesting, protect
# the mirror's own git directory, and skip the usual generated files.
rsync -av --delete \
    --exclude='Kimi_Sandbox' \
    --exclude='/.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='server.log' \
    --exclude='.DS_Store' \
    "${SOURCE}/" "${MIRROR}/"

cd "$MIRROR"

# Stage everything so new, modified, and deleted files are reflected.
git add -A

if git diff --cached --quiet; then
    echo "Mirror is already up to date."
    exit 0
fi

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
COMMIT_MSG="Sync terrarium state at ${TS}"

# Append the current garden step to the commit message when available.
if [[ -f "$SOURCE/garden.json" ]]; then
    GARDEN_STATUS=$(python3 -c '
import json, sys
try:
    with open("/srv/terrarium/space/garden.json") as f:
        data = json.load(f)
    step = data.get("step", "?")
    plants = len(data.get("plants", []))
    print(f"garden step {step} with {plants} plants")
except Exception:
    pass
')
    [[ -n "$GARDEN_STATUS" ]] && COMMIT_MSG="${COMMIT_MSG} — ${GARDEN_STATUS}"
fi

git commit -m "$COMMIT_MSG"
git push origin main

echo "Mirror synced and pushed: $COMMIT_MSG"
