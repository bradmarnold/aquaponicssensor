#!/usr/bin/env bash
set -euo pipefail
cd /home/pi/aquaponicssensor
mkdir -p docs
cp -f data.json summaries.json coach.json docs/ 2>/dev/null || true
git add docs/data.json docs/summaries.json docs/coach.json 2>/dev/null || true
git commit -m "chore: update telemetry $(date -u +%FT%TZ)" || true
git push origin main
