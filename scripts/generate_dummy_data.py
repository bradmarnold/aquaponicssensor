#!/usr/bin/env python3
"""
generate_dummy_data.py - Generate dummy sensor data for testing
============================================================

Generates zero-valued or realistic dummy data for testing the dashboard
and coach functionality. Creates data.json with entries every 30 minutes
for the specified number of days.

Usage:
  python3 generate_dummy_data.py [options]
  
Options:
  --days N         Number of days to generate (default: 60)
  --step-min N     Minutes between readings (default: 30)  
  --outfile FILE   Output file path (default: ../data.json)
  --zeros          Generate zero values (default, for seeding)
  --realistic      Generate realistic aquaponics values with variation
  
Examples:
  python3 generate_dummy_data.py --days 60 --zeros
  python3 generate_dummy_data.py --days 7 --realistic --outfile test_data.json
"""

import argparse
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


def generate_realistic_reading(timestamp, base_values=None):
    """Generate a realistic sensor reading with natural variation.
    
    Args:
        timestamp (datetime): Reading timestamp
        base_values (dict): Base values for variation, or None for defaults
        
    Returns:
        dict: Realistic sensor reading
    """
    if base_values is None:
        base_values = {
            "ph": 6.8,      # Typical aquaponics pH
            "tds": 350,     # Typical aquaponics TDS in ppm
            "temp_c": 24.5  # Typical water temperature
        }
    
    # Add daily/seasonal cycles and random variation
    hour = timestamp.hour
    day_of_year = timestamp.timetuple().tm_yday
    
    # Daily temperature cycle (warmer in afternoon)
    temp_daily_variation = 2.0 * math.sin((hour - 6) * math.pi / 12)
    # Seasonal variation (simplified)
    temp_seasonal_variation = 3.0 * math.sin((day_of_year - 81) * 2 * math.pi / 365)
    
    # pH tends to rise slightly during the day (photosynthesis)
    ph_daily_variation = 0.2 * math.sin((hour - 8) * math.pi / 12)
    
    # TDS fluctuates with feeding cycles and evaporation
    tds_daily_variation = 20 * math.sin((hour - 4) * 2 * math.pi / 24)
    
    # Add random noise
    ph = base_values["ph"] + ph_daily_variation + random.gauss(0, 0.1)
    tds = base_values["tds"] + tds_daily_variation + random.gauss(0, 15)
    temp_c = (base_values["temp_c"] + temp_daily_variation + 
              temp_seasonal_variation + random.gauss(0, 0.5))
    
    # Constrain to reasonable ranges
    ph = max(6.0, min(8.0, ph))
    tds = max(100, min(800, tds))
    temp_c = max(15.0, min(30.0, temp_c))
    
    return {
        "timestamp": timestamp.isoformat().replace('+00:00', 'Z'),
        "ph": round(ph, 3),
        "tds": round(tds, 1),
        "temp_c": round(temp_c, 2)
    }


def generate_zero_reading(timestamp):
    """Generate a zero-valued reading for seeding purposes.
    
    Args:
        timestamp (datetime): Reading timestamp
        
    Returns:
        dict: Zero-valued sensor reading
    """
    return {
        "timestamp": timestamp.isoformat().replace('+00:00', 'Z'), 
        "ph": 0.0,
        "tds": 0.0,
        "temp_c": 0.0
    }


def generate_dummy_data(days, step_minutes, use_zeros=True, base_values=None):
    """Generate dummy sensor data for specified time period.
    
    Args:
        days (int): Number of days to generate
        step_minutes (int): Minutes between readings
        use_zeros (bool): If True, generate zero values; if False, realistic values
        base_values (dict): Base values for realistic data generation
        
    Returns:
        list: Array of sensor readings
    """
    readings = []
    
    # Start from N days ago
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    
    current_time = start_time
    step_delta = timedelta(minutes=step_minutes)
    
    print(f"Generating data from {start_time} to {end_time}")
    print(f"Step: {step_minutes} minutes, Mode: {'zeros' if use_zeros else 'realistic'}")
    
    while current_time <= end_time:
        if use_zeros:
            reading = generate_zero_reading(current_time)
        else:
            reading = generate_realistic_reading(current_time, base_values)
        
        readings.append(reading)
        current_time += step_delta
    
    return readings


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Generate dummy aquaponics sensor data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 60 days of zero data (for seeding charts)
  python3 generate_dummy_data.py --days 60 --zeros
  
  # Generate 7 days of realistic data for testing
  python3 generate_dummy_data.py --days 7 --realistic
  
  # Generate data every 15 minutes to a custom file
  python3 generate_dummy_data.py --step-min 15 --outfile test.json
        """
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=60,
        help='Number of days to generate (default: 60)'
    )
    
    parser.add_argument(
        '--step-min',
        type=int, 
        default=30,
        help='Minutes between readings (default: 30)'
    )
    
    parser.add_argument(
        '--outfile',
        type=str,
        default='../data.json',
        help='Output file path (default: ../data.json)'
    )
    
    # Mutually exclusive group for data type
    data_type = parser.add_mutually_exclusive_group()
    data_type.add_argument(
        '--zeros',
        action='store_true',
        default=True,
        help='Generate zero values (default)'
    )
    data_type.add_argument(
        '--realistic', 
        action='store_true',
        help='Generate realistic aquaponics values'
    )
    
    args = parser.parse_args()
    
    # Resolve output file path
    output_path = Path(args.outfile)
    if not output_path.is_absolute():
        # Relative to script directory
        output_path = Path(__file__).parent / args.outfile
    
    print("Dummy Data Generator")
    print("=" * 40)
    
    # Generate data
    use_zeros = not args.realistic  # Default to zeros unless --realistic specified
    readings = generate_dummy_data(
        days=args.days,
        step_minutes=args.step_min,
        use_zeros=use_zeros
    )
    
    # Save to file
    try:
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(readings, f, indent=2)
        
        print(f"Generated {len(readings)} readings")
        print(f"Saved to: {output_path.absolute()}")
        
        # Show sample of generated data
        if readings:
            print("\nSample readings:")
            for i in [0, len(readings)//2, -1]:
                if i < len(readings):
                    r = readings[i]
                    print(f"  {r['timestamp']}: pH={r['ph']}, TDS={r['tds']}, Temp={r['temp_c']}")
        
    except Exception as e:
        print(f"Error saving data: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())