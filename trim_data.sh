#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Config (override by env): DAYS=90 DROP_NULLS=1
DAYS="${DAYS:-90}"
DROP_NULLS="${DROP_NULLS:-1}"
MIN_KEEP="${MIN_KEEP:-200}"     # if filter is too aggressive, keep at least this many latest rows

DATA="data.json"
BACKUP="data.backup.$(date -u +%F).json"
TMP="$(mktemp)"

cp -f "$DATA" "$BACKUP"

python3 - <<PY "$DATA" "$TMP" "$DAYS" "$DROP_NULLS" "$MIN_KEEP"
import json, sys
from datetime import datetime, timezone, timedelta
SRC, DST, DAYS, DROP_NULLS, MIN_KEEP = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])

def parse_ts(s):
    s = str(s)
    if s.endswith("Z"): s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        try:
            dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")
        except Exception:
            return None
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

now = datetime.now(timezone.utc)
cutoff = now - timedelta(days=DAYS)

data = json.load(open(SRC))
# Normalize + keep original order
rows = []
for r in data:
    dt = parse_ts(r.get("timestamp"))
    if not dt: continue
    r["timestamp"] = dt.isoformat()
    rows.append(r)

filtered = [
    r for r in rows
    if parse_ts(r["timestamp"]) >= cutoff and (
        not DROP_NULLS or (
            r.get("ph")   is not None and
            r.get("tds")  is not None and
            r.get("temp_c") is not None
        )
    )
]

# Ensure we never publish an almost-empty file
if len(filtered) < MIN_KEEP and rows:
    filtered = rows[-MIN_KEEP:]

# Write pretty JSON
json.dump(filtered, open(DST, "w"), indent=2)
print(f"Kept {len(filtered)} of {len(rows)} rows; cutoff={cutoff.isoformat()}")
PY

mv "$TMP" "$DATA"

# Publish to Pages
mkdir -p docs
cp -f "$DATA" docs/data.json
git add docs/data.json
git commit -m "data: trim to last ${DAYS}d (drop_nulls=${DROP_NULLS})" || true
git push origin main
