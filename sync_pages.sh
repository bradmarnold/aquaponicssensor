#!/usr/bin/env bash
set -euo pipefail
cd /home/pi/aquaponicssensor

# build summaries every time
/usr/bin/python3 pi/build_summaries.py

mkdir -p docs
cp -f data.json summaries.json coach.json docs/

git config user.name  "raspi-bot"        >/dev/null
git config user.email "raspi@example.com" >/dev/null
rm -f .git/index.lock || true

git add docs/data.json docs/summaries.json docs/coach.json
git commit -m "pages: update telemetry $(date -u +%FT%TZ)" || true

# push to whichever branch we are on
BRANCH=$(git rev-parse --abbrev-ref HEAD || echo main)
git push origin "$BRANCH"
