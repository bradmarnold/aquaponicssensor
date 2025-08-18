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
        
        # Parse timestamps and filter valid entries
        parsed_data = []
        for entry in data:
            try:
                if isinstance(entry, dict) and "timestamp" in entry:
                    timestamp_str = entry["timestamp"]
                    timestamp = datetime.fromisoformat(timestamp_str.rstrip('Z'))
                    
                    parsed_entry = {
                        "timestamp": timestamp,
                        "ph": entry.get("ph"),
                        "tds": entry.get("tds"), 
                        "temp_c": entry.get("temp_c")
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
    """Analyze sensor data and compute summary statistics.
    
    Args:
        data (list): Array of readings with parsed timestamps
        
    Returns:
        dict: Analysis results with 7-day and 30-day stats
    """
    now = datetime.now(timezone.utc)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)
    
    # Filter data by time periods
    data_7d = [entry for entry in data if entry["timestamp"] >= cutoff_7d]
    data_30d = [entry for entry in data if entry["timestamp"] >= cutoff_30d]
    
    print(f"Analyzing {len(data_7d)} readings from last 7 days")
    print(f"Analyzing {len(data_30d)} readings from last 30 days")
    
    analysis = {
        "last_7_days": {
            "period": "7 days",
            "count": len(data_7d),
            "ph": compute_stats(data_7d, "ph"),
            "tds": compute_stats(data_7d, "tds"),
            "temp": compute_stats(data_7d, "temp_c")
        },
        "last_30_days": {
            "period": "30 days", 
            "count": len(data_30d),
            "ph": compute_stats(data_30d, "ph"),
            "tds": compute_stats(data_30d, "tds"),
            "temp": compute_stats(data_30d, "temp_c")
        },
        "targets": TARGETS
    }
    
    return analysis


def build_coaching_prompt(analysis):
    """Build prompt for OpenAI coaching request.
    
    Args:
        analysis (dict): Data analysis results
        
    Returns:
        str: Formatted prompt text
    """
    prompt = f"""You are an expert aquaponics water quality coach. Analyze this sensor data and provide coaching advice.

## Data Summary

### Last 7 Days ({analysis['last_7_days']['count']} readings):
- pH: {analysis['last_7_days']['ph']}
- TDS: {analysis['last_7_days']['tds']} ppm
- Temperature: {analysis['last_7_days']['temp']} °C

### Last 30 Days ({analysis['last_30_days']['count']} readings):
- pH: {analysis['last_30_days']['ph']}  
- TDS: {analysis['last_30_days']['tds']} ppm
- Temperature: {analysis['last_30_days']['temp']} °C

## Target Ranges:
- pH: {analysis['targets']['ph']['min']}-{analysis['targets']['ph']['max']} (ideal: {analysis['targets']['ph']['ideal']})
- TDS: {analysis['targets']['tds']['min']}-{analysis['targets']['tds']['max']} ppm (ideal: {analysis['targets']['tds']['ideal']}) - {analysis['targets']['tds']['note']}
- Temperature: {analysis['targets']['temp']['note']}

Please provide:
1. Overall system status (ok/watch/alert)
2. Brief summary of water quality 
3. Specific insights and recommendations for each metric

Focus on practical, actionable advice for aquaponics system management."""

    return prompt


def call_openai_responses_api(prompt):
    """Call OpenAI Responses API with structured outputs.
    
    Args:
        prompt (str): Coaching prompt text
        
    Returns:
        dict: Structured coaching response or None if error
    """
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY environment variable not set")
        return None
    
    # Define structured output schema
    response_schema = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["ok", "watch", "alert"]
            },
            "summary": {
                "type": "string"
            },
            "insights": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "metric": {
                            "type": "string", 
                            "enum": ["ph", "tds", "temp"]
                        },
                        "trend": {
                            "type": "string"
                        },
                        "risk": {
                            "type": "string"
                        },
                        "recommendation": {
                            "type": "string"
                        }
                    },
                    "required": ["metric", "recommendation"]
                }
            },
            "timestamp": {
                "type": "string"
            }
        },
        "required": ["status", "summary", "insights"]
    }
    
    # Build API request
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are an expert aquaponics consultant providing water quality coaching advice."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "coaching_response",
                "schema": response_schema,
                "strict": True
            }
        },
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        print(f"Calling OpenAI API with model {OPENAI_MODEL}...")
        
        response = requests.post(
            OPENAI_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"OpenAI API error {response.status_code}: {response.text}")
            return None
        
        result = response.json()
        
        if "choices" not in result or not result["choices"]:
            print("Error: No choices returned from OpenAI API")
            return None
        
        content = result["choices"][0]["message"]["content"]
        
        try:
            coaching_data = json.loads(content)
            # Add timestamp if not provided
            if "timestamp" not in coaching_data:
                coaching_data["timestamp"] = datetime.now(timezone.utc).isoformat()
            return coaching_data
            
        except json.JSONDecodeError as e:
            print(f"Error parsing OpenAI response as JSON: {e}")
            print(f"Response content: {content}")
            return None
        
    except requests.exceptions.Timeout:
        print("Error: OpenAI API request timed out")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenAI API: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error calling OpenAI API: {e}")
        return None


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
        save_coaching_data(coaching_data)
        print(f"Generated coaching advice: {coaching_data['status']} status")
        print(f"Summary: {coaching_data['summary']}")
    else:
        print("Failed to generate coaching advice")
        sys.exit(1)


if __name__ == "__main__":
    main()