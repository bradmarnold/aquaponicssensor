#!/usr/bin/env python3
"""
coach.py - Aquaponics Water Coach AI Assistant
==============================================

Analyzes last 30 days of sensor data and generates coaching advice using 
OpenAI's Responses API with Structured Outputs.

Loads data from ../data.json, computes statistics for last 7 and 30 days,
and calls OpenAI to generate insights and recommendations.

Environment Variables:
- OPENAI_API_KEY (required) - OpenAI API key 
- OPENAI_MODEL=gpt-4o-mini - Model to use (default: gpt-4o-mini)

Usage:
  python3 coach.py
  
Output: ../coach.json with structured coaching advice
"""

import json
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone

def _to_aware(ts):
    """
    Return a timezone-aware UTC datetime from either a string or a datetime.
    Accepts '...Z' and '...+00:00'. Treats naive datetimes as UTC.
    """
    if isinstance(ts, str):
        if ts.endswith('Z'):
            ts = ts.replace('Z', '+00:00')
        dt = datetime.fromisoformat(ts)
    elif isinstance(ts, datetime):
        dt = ts
    else:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests library not available. Install with: pip install requests")
    sys.exit(1)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
COACH_SPECIES = os.getenv("COACH_SPECIES", "Blue Nile tilapia")
COACH_PLANTS  = os.getenv("COACH_PLANTS",  "basil, peppers")

# File paths
DATA_FILE = Path(__file__).parent.parent / "data.json"
COACH_FILE = Path(__file__).parent.parent / "coach.json"

# Target ranges for coaching
TARGETS = {
    "ph": {"min": 6.6, "max": 7.2, "ideal": 6.9},
    "tds": {"min": 200, "max": 500, "ideal": 350, "unit": "ppm", "note": "freshwater aquaponics"},
    "temp": {"note": "species dependent, typically 18-28°C for most fish"}
}


def load_sensor_data():
    """Load and parse sensor data from data.json.

    Returns:
        list: Array of reading dicts with parsed timestamps
    """
    if not DATA_FILE.exists():
        print(f"Warning: {DATA_FILE} not found")
        return []

    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("Warning: data.json should contain an array")
            return []

        parsed_data = []
        for entry in data:
            try:
                if isinstance(entry, dict):
                    ts_raw = entry.get("timestamp") or entry.get("ts")
                    ts_dt = _to_aware(ts_raw)
                    if ts_dt is None:
                        continue
                    parsed_entry = {
                        "timestamp": ts_dt,       # aware UTC datetime
                        "ph": entry.get("ph"),
                        "tds": entry.get("tds"),
                        "temp_c": entry.get("temp_c"),
                    }
                    parsed_data.append(parsed_entry)
            except Exception as e:
                print(f"Warning: Skipping malformed entry: {e}")
                continue

        print(f"Loaded {len(parsed_data)} valid readings")
        return parsed_data

    except Exception as e:
        print(f"Error loading sensor data: {e}")
        return []


def compute_stats(data, metric):
    """Compute statistics for a metric, ignoring None values.
    
    Args:
        data (list): Array of readings
        metric (str): Metric name ('ph', 'tds', 'temp_c')
        
    Returns:
        dict: Statistics (count, min, max, avg, median) or None if no data
    """
    values = [entry[metric] for entry in data if entry[metric] is not None]
    
    if not values:
        return None
    
    try:
        return {
            "count": len(values),
            "min": round(min(values), 2),
            "max": round(max(values), 2), 
            "avg": round(statistics.mean(values), 2),
            "median": round(statistics.median(values), 2)
        }
    except Exception as e:
        print(f"Error computing stats for {metric}: {e}")
        return None

def analyze_data(data):
    """Analyze sensor data and compute summary statistics."""
    now = datetime.now(timezone.utc)
    cutoff_7d  = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    # Normalize rows to aware UTC datetimes
    norm = []
    for e in data:
        try:
            ts = e.get("timestamp") or e.get("ts")
            ts_dt = _to_aware(ts)
            if ts_dt is None:
                continue
            row = dict(e)
            row["timestamp"] = ts_dt
            norm.append(row)
        except Exception:
            continue

    # Safe sort (numeric epoch avoids any residual type quirks)
    norm.sort(key=lambda r: r["timestamp"].timestamp())

    # Windows
    data_7d  = [r for r in norm if r["timestamp"] >= cutoff_7d]
    data_30d = [r for r in norm if r["timestamp"] >= cutoff_30d]

    print(f"Analyzing {len(data_7d)} readings from last 7 days")
    print(f"Analyzing {len(data_30d)} readings from last 30 days")

    analysis = {
        "last_7_days": {
            "period": "7 days",
            "count": len(data_7d),
            "ph":   compute_stats(data_7d,  "ph"),
            "tds":  compute_stats(data_7d,  "tds"),
            "temp": compute_stats(data_7d,  "temp_c"),
        },
        "last_30_days": {
            "period": "30 days",
            "count": len(data_30d),
            "ph":   compute_stats(data_30d, "ph"),
            "tds":  compute_stats(data_30d, "tds"),
            "temp": compute_stats(data_30d, "temp_c"),
        },
        "targets": TARGETS,
    }
    return analysis


def build_coaching_prompt(analysis):
    ctx = (
        f"Fish: {COACH_SPECIES}. Plants: {COACH_PLANTS}. "
        "Operate for nitrifying bacteria, fish health, and plant uptake together."
    )
    prompt = f"""Using the system context below, analyze the data and give concise, actionable advice.

System Context:
- {ctx}
- Targets: pH 6.6–7.2 (ideal ~6.9); TDS 200–500 ppm (ideal ~350); Temp 24–28°C.

Data Summary
Last 7 Days ({analysis['last_7_days']['count']} readings)
- pH: {analysis['last_7_days']['ph']}
- TDS: {analysis['last_7_days']['tds']} ppm
- Temp: {analysis['last_7_days']['temp']} °C

Last 30 Days ({analysis['last_30_days']['count']} readings)
- pH: {analysis['last_30_days']['ph']}
- TDS: {analysis['last_30_days']['tds']} ppm
- Temp: {analysis['last_30_days']['temp']} °C

Instructions:
- Use the targets above (not generic hydroponics ranges).
- Recommendations should be specific to Blue Nile tilapia + basil/peppers aquaponics.
- Keep each recommendation to one practical sentence (e.g., buffer up/down, partial water change, shade/aeration/heater).
- If data is insufficient, say so briefly.
"""
    return prompt



def call_openai_responses_api(prompt):
    """Call OpenAI Chat Completions API and ask for a strict JSON object."""
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY environment variable not set")
        return None

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    system_msg = (
    "You are an expert aquaponics consultant. "
    f"System context: fish species={COACH_SPECIES}; plants={COACH_PLANTS}. "
    "Target operating ranges for this system:\n"
    "- pH: 6.6–7.2 (ideal ~6.9) to balance nitrification, tilapia tolerance, and plant uptake.\n"
    "- TDS: 200–500 ppm (ideal ~350 ppm) for this aquaponics setup.\n"
    "- Water temp: 24–28°C (tilapia-safe; plants basil/peppers okay in this window).\n"
    "Return ONLY a single JSON object with EXACT keys:\n"
    "status (one of: ok, watch, alert),\n"
    "summary (<= 1 sentence, plain text),\n"
    "insights (array with exactly 3 items in this order: ph, tds, temp; "
    "each item has: metric('ph'|'tds'|'temp'), trend(short phrase), recommendation(actionable one-liner for this system)),\n"
    "timestamp (ISO 8601, UTC).\n"
    "No extra keys, no nested objects except within each insight item, no markdown, no code fences."
"Tone/style: concise, practical, aquaponics-aware. Use simple present tense. "
"Avoid hedging language; give clear one-line actions per metric."

)


    payload = {
        "model": OPENAI_MODEL,  # e.g., gpt-4o-mini or gpt-4-0613
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
        "max_tokens": 1000,
    }

    try:
        print(f"Calling OpenAI API with model {OPENAI_MODEL}...")
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=45,
        )

        if response.status_code != 200:
            print(f"OpenAI API error {response.status_code}: {response.text}")
            return None

        result = response.json()
        content = result["choices"][0]["message"]["content"]
        coaching_data = json.loads(content)

        if "timestamp" not in coaching_data:
            coaching_data["timestamp"] = datetime.now(timezone.utc).isoformat()

        return coaching_data

    except requests.exceptions.Timeout:
        print("Error: OpenAI API request timed out")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenAI API: {e}")
        return None
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error parsing OpenAI JSON: {e}")
        try:
            print(f"Raw content (first 400 chars): {content[:400]}")
        except Exception:
            pass
        return None
    except Exception as e:
        print(f"Unexpected error calling OpenAI API: {e}")
        return None


def _normalize_coach_payload(coaching_data):
    """
    Coerce various model outputs into {status, summary, insights, timestamp}.
    Accepts either:
      - {status, summary, insights, timestamp}
      - {overall_system_status, water_quality_summary, insights_and_recommendations, timestamp}
    """
    out = {}

    # status
    out["status"] = (
        coaching_data.get("status")
        or coaching_data.get("overall_system_status")
        or "unknown"
    )

    # summary
    summary = coaching_data.get("summary")
    if summary is None:
        wqs = coaching_data.get("water_quality_summary")
        summary = "See water_quality_summary in coach.json" if isinstance(wqs, dict) else (wqs if wqs is not None else "")
    out["summary"] = summary

    # insights -> list of {metric, trend, recommendation, risk?}
    if isinstance(coaching_data.get("insights"), list):
        insights_list = coaching_data["insights"]
    else:
        insights_list = []
        iandr = coaching_data.get("insights_and_recommendations", {})
        if isinstance(iandr, dict):
            for metric, obj in iandr.items():
                if isinstance(obj, dict):
                    insights_list.append({
                        "metric": str(metric).lower(),
                        "trend": obj.get("insight"),
                        "risk": obj.get("risk"),  # may be None
                        "recommendation": obj.get("recommendation"),
                    })
    out["insights"] = insights_list

    # timestamp
    out["timestamp"] = coaching_data.get("timestamp", datetime.now(timezone.utc).isoformat())

    return out





def save_coaching_data(coaching_data):
    """Save coaching data to coach.json file.
    
    Args:
        coaching_data (dict): Structured coaching response
    """
    try:
        with open(COACH_FILE, 'w') as f:
            json.dump(coaching_data, f, indent=2)
        print(f"Saved coaching advice to {COACH_FILE}")
    except Exception as e:
        print(f"Error saving coaching data: {e}")


def main():
    """Main entry point for coach generation."""
    print("Aquaponics Water Coach")
    print("=" * 40)

    # Load and analyze sensor data
    data = load_sensor_data()
    if not data:
        print("Error: No sensor data available for analysis")
        sys.exit(1)

    analysis = analyze_data(data)

    # Build prompt and call OpenAI
    prompt = build_coaching_prompt(analysis)
    coaching_data = call_openai_responses_api(prompt)

    if coaching_data:
        normalized = _normalize_coach_payload(coaching_data)
    # after you build `normalized` (or right after parsing `coaching_data`)
    from datetime import datetime, timezone
    normalized["timestamp"] = datetime.now(timezone.utc).isoformat()
        save_coaching_data(normalized)
     print(f"Generated coaching advice: {normalized['status']} status")
        # If summary is a big dict, just say where to look
        print(f"Summary: {normalized['summary']}")
    else:
        print("Failed to generate coaching advice")
        sys.exit(1)


if __name__ == "__main__":
    main()

