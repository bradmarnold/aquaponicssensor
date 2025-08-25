#!/usr/bin/env bash
set -euo pipefail
# Load env (OPENAI_API_KEY, calibration, channel maps, etc.)
. /etc/environment || true
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"

cd /home/pi/aquaponicssensor
git fetch origin && git checkout main && git pull --ff-only || true

# 1) Read sensors
python3 pi/sensor_logger.py --once || true

# 2) Generate coach (will use OpenAI if available, otherwise local fallback)
python3 pi/coach.py || true

# 3) Publish to Pages
mkdir -p docs
cp -f data.json  docs/data.json
cp -f coach.json docs/coach.json
git add docs/data.json docs/coach.json
git commit -m "pages: auto publish $(date -u +%FT%TZ)" || true
git push origin main || true
