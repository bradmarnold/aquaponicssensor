#!/usr/bin/env python3
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data.json"
OUT  = ROOT / "summaries.json"

def parse(ts):
    return datetime.fromisoformat(ts.replace("Z","+00:00")).astimezone(timezone.utc)

def daily_avgs(rows):
    days = {}
    for r in rows:
        d = parse(r["timestamp"]).date().isoformat()
        days.setdefault(d, {"ph": [], "tds": [], "temp_c": []})
        for k in ("ph","tds","temp_c"):
            if r.get(k) is not None:
                days[d][k].append(r[k])
    out=[]
    for d,vals in sorted(days.items()):
        def avg(a): return round(sum(a)/len(a),2) if a else None
        out.append({"date": d,
                    "ph":   avg(vals["ph"]),
                    "tds":  avg(vals["tds"]),
                    "temp_c": avg(vals["temp_c"])})
    return out

def main():
    if not DATA.exists():
        print("no data.json")
        return
    data = json.load(open(DATA)) or []
    now = datetime.now(timezone.utc)
    last7  = [r for r in data if parse(r["timestamp"]) >= now - timedelta(days=7)]
    last30 = [r for r in data if parse(r["timestamp"]) >= now - timedelta(days=30)]
    out = {
        "last7_raw": last7,
        "last30_daily_avg": daily_avgs(last30)
    }
    json.dump(out, open(OUT,"w"), indent=2)
    print(f"wrote {OUT}")
if __name__ == "__main__":
    main()
