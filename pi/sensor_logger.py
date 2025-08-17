#!/usr/bin/env python3
"""
sensor_logger.py - Raspberry Pi Aquaponics Sensor Logger
========================================================

Reads pH, TDS, and water temperature from sensors connected via ADS1115 ADC and DS18B20.
Stores readings in data.json with configurable retention window and optional git push.

Hardware Setup:
- DFRobot Gravity pH Kit V2 (SEN0161-V2) → ADS1115 A0
- DFRobot Gravity TDS Sensor (SEN0244) → ADS1115 A1  
- DS18B20 waterproof temperature probe → GPIO4 (1-Wire, with 4.7 kΩ pull-up to 3.3V)
- ADS1115 connected over I²C (SDA=GPIO2, SCL=GPIO3, VCC=3.3V)

Environment Variables (with defaults):
- WINDOW_DAYS=60 - Days of data to retain
- ADS1115_ADDR=0x48 - I2C address of ADS1115
- ADC_CH_PH=0 - ADS1115 channel for pH sensor
- ADC_CH_TDS=1 - ADS1115 channel for TDS sensor  
- PH_SLOPE=-3.333 - pH calibration slope (user calibrates)
- PH_INTERCEPT=12.5 - pH calibration intercept (user calibrates)
- TDS_MULTIPLIER=0.5 - TDS scaling factor (NaCl scale, user calibrates)
- GIT_PUSH=0 - If "1", run git add/commit/push after each reading

Usage:
  python3 sensor_logger.py [--once]
  
  --once: Take one reading then exit (for testing)
  Default: Run as daemon with 30-minute intervals
"""

import argparse
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import board
    import busio
    from adafruit_ads1x15.ads1115 import ADS1115
    from adafruit_ads1x15.analog_in import AnalogIn
except ImportError:
    print("Warning: Adafruit libraries not available. Mock mode enabled.")
    ADS1115 = None
    AnalogIn = None

# Configuration from environment
WINDOW_DAYS = int(os.getenv("WINDOW_DAYS", "60"))
ADS1115_ADDR = int(os.getenv("ADS1115_ADDR", "0x48"), 16)
ADC_CH_PH = int(os.getenv("ADC_CH_PH", "0"))
ADC_CH_TDS = int(os.getenv("ADC_CH_TDS", "1"))
PH_SLOPE = float(os.getenv("PH_SLOPE", "-3.333"))
PH_INTERCEPT = float(os.getenv("PH_INTERCEPT", "12.5"))
TDS_MULTIPLIER = float(os.getenv("TDS_MULTIPLIER", "0.5"))
GIT_PUSH = os.getenv("GIT_PUSH", "0") == "1"

# Data file path
DATA_FILE = Path(__file__).parent.parent / "data.json"


def init_ads1115():
    """Initialize ADS1115 ADC and return channel objects for pH and TDS."""
    if ADS1115 is None:
        print("Warning: Running in mock mode - no hardware access")
        return None, None
    
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        adc = ADS1115(i2c, address=ADS1115_ADDR)
        
        # Map channel numbers to ADS1115 pins
        pin_map = {0: ADS1115.P0, 1: ADS1115.P1, 2: ADS1115.P2, 3: ADS1115.P3}
        
        chan_ph = AnalogIn(adc, pin_map[ADC_CH_PH])
        chan_tds = AnalogIn(adc, pin_map[ADC_CH_TDS])
        
        print(f"ADS1115 initialized at address 0x{ADS1115_ADDR:02x}")
        print(f"pH sensor on channel {ADC_CH_PH}, TDS sensor on channel {ADC_CH_TDS}")
        
        return chan_ph, chan_tds
    except Exception as e:
        print(f"Error initializing ADS1115: {e}")
        return None, None


def read_ds18b20():
    """Read temperature from DS18B20 sensor on 1-Wire bus.
    
    Returns:
        float: Temperature in Celsius, or None if read fails
    """
    try:
        base_dir = "/sys/bus/w1/devices"
        if not os.path.exists(base_dir):
            return None
            
        # Find first DS18B20 device
        device_folders = [d for d in os.listdir(base_dir) if d.startswith("28-")]
        if not device_folders:
            return None
            
        device_file = Path(base_dir) / device_folders[0] / "w1_slave"
        if not device_file.exists():
            return None
            
        with open(device_file) as f:
            lines = f.read().strip().split('\n')
            
        # Check CRC
        if len(lines) < 2 or not lines[0].endswith('YES'):
            return None
            
        # Extract temperature
        temp_line = lines[1]
        if 't=' not in temp_line:
            return None
            
        temp_string = temp_line.split('t=')[1]
        temp_c = float(temp_string) / 1000.0
        
        return temp_c
        
    except Exception as e:
        print(f"Error reading DS18B20: {e}")
        return None


def voltage_to_ph(voltage):
    """Convert pH sensor voltage to pH value using calibration parameters.
    
    Args:
        voltage (float): Sensor voltage in volts
        
    Returns:
        float: pH value, or None if out of plausible range
    """
    if voltage is None or not (0.0 <= voltage <= 5.0):
        return None
        
    # Skip pH conversion if slope is 0 (sensor not available yet)
    if PH_SLOPE == 0:
        return None
        
    ph = PH_SLOPE * voltage + PH_INTERCEPT
    
    # Guard against implausible pH values
    if not (0.0 <= ph <= 14.0):
        return None
        
    return round(ph, 3)


def voltage_to_tds(voltage, temp_c):
    """Convert TDS sensor voltage to ppm using DFRobot polynomial and temperature compensation.
    
    Args:
        voltage (float): Sensor voltage in volts
        temp_c (float): Water temperature in Celsius
        
    Returns:
        float: TDS in ppm, or None if invalid inputs
    """
    if voltage is None or temp_c is None:
        return None
        
    if not (0.0 <= voltage <= 5.0) or not (-10.0 <= temp_c <= 60.0):
        return None
    
    try:
        # Temperature compensation (25°C reference)
        compensation_coefficient = 1.0 + 0.02 * (temp_c - 25.0)
        if compensation_coefficient <= 0:
            compensation_coefficient = 1.0
            
        compensation_voltage = voltage / compensation_coefficient
        
        # DFRobot polynomial for EC (µS/cm)
        ec = (
            133.42 * compensation_voltage ** 3
            - 255.86 * compensation_voltage ** 2
            + 857.39 * compensation_voltage
        )
        
        # Convert EC to TDS using multiplier (typically 0.5 for NaCl)
        tds = max(ec * TDS_MULTIPLIER, 0.0)
        
        # Guard against implausible TDS values (0-5000 ppm range)
        if tds > 5000:
            return None
            
        return round(tds, 1)
        
    except Exception as e:
        print(f"Error calculating TDS: {e}")
        return None


def read_sensors(chan_ph, chan_tds):
    """Read all sensors and return formatted data dict.
    
    Args:
        chan_ph: ADS1115 pH channel object (or None in mock mode)
        chan_tds: ADS1115 TDS channel object (or None in mock mode)
        
    Returns:
        dict: Reading with timestamp, ph, tds, temp_c fields
    """
    # Read raw sensor values
    if chan_ph is not None and chan_tds is not None:
        try:
            ph_voltage = chan_ph.voltage
            tds_voltage = chan_tds.voltage
        except Exception as e:
            print(f"Error reading ADS1115: {e}")
            ph_voltage = None
            tds_voltage = None
    else:
        # Mock mode - return None values
        ph_voltage = None
        tds_voltage = None
    
    temp_c = read_ds18b20()
    
    # Convert to sensor values
    ph = voltage_to_ph(ph_voltage)
    tds = voltage_to_tds(tds_voltage, temp_c)
    
    # Create reading dict - None values are preserved
    reading = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ph": ph,
        "tds": tds,
        "temp_c": temp_c
    }
    
    return reading


def load_data():
    """Load existing data from JSON file.
    
    Returns:
        list: Array of reading dicts, empty if file doesn't exist
    """
    if not DATA_FILE.exists():
        return []
        
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error loading data file: {e}")
        return []


def save_data(data):
    """Save data array to JSON file.
    
    Args:
        data (list): Array of reading dicts
    """
    try:
        # Ensure parent directory exists
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Saved {len(data)} readings to {DATA_FILE}")
    except Exception as e:
        print(f"Error saving data: {e}")


def prune_old_data(data):
    """Remove readings older than WINDOW_DAYS.
    
    Args:
        data (list): Array of reading dicts
        
    Returns:
        list: Filtered array with recent readings only
    """
    if not data:
        return data
        
    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    pruned = []
    
    for entry in data:
        try:
            timestamp_str = entry.get("timestamp", "")
            timestamp = datetime.fromisoformat(timestamp_str.rstrip('Z'))
            if timestamp >= cutoff:
                pruned.append(entry)
        except Exception:
            # Skip malformed entries
            continue
    
    removed = len(data) - len(pruned)
    if removed > 0:
        print(f"Pruned {removed} old readings (keeping {WINDOW_DAYS} days)")
    
    return pruned


def git_push_data():
    """Add, commit and push data.json using git commands.
    
    Only runs if GIT_PUSH environment variable is "1".
    """
    if not GIT_PUSH:
        return
        
    try:
        # Change to repo root directory
        repo_root = DATA_FILE.parent
        
        # Git add data.json
        result = subprocess.run(
            ["git", "add", "data.json"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"Git add failed: {result.stderr}")
            return
        
        # Git commit
        commit_msg = f"Update sensor data at {datetime.now(timezone.utc).isoformat()}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            # Might be no changes to commit
            if "nothing to commit" in result.stdout:
                print("No changes to commit")
                return
            else:
                print(f"Git commit failed: {result.stderr}")
                return
        
        # Git push
        result = subprocess.run(
            ["git", "push"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"Git push failed: {result.stderr}")
        else:
            print("Successfully pushed data to git repository")
            
    except subprocess.TimeoutExpired:
        print("Git operation timed out")
    except Exception as e:
        print(f"Error during git push: {e}")


def take_reading(chan_ph, chan_tds):
    """Take one sensor reading and update data file.
    
    Args:
        chan_ph: ADS1115 pH channel object
        chan_tds: ADS1115 TDS channel object
    """
    try:
        # Read sensors
        reading = read_sensors(chan_ph, chan_tds)
        print(f"Reading: {reading}")
        
        # Load existing data
        data = load_data()
        
        # Add new reading
        data.append(reading)
        
        # Prune old data
        data = prune_old_data(data)
        
        # Save to file
        save_data(data)
        
        # Optional git push
        git_push_data()
        
    except Exception as e:
        print(f"Error taking reading: {e}")


def run_daemon(chan_ph, chan_tds):
    """Run continuous monitoring with 30-minute intervals.
    
    Args:
        chan_ph: ADS1115 pH channel object
        chan_tds: ADS1115 TDS channel object
    """
    print("Starting sensor logger daemon (30-minute intervals)")
    print(f"Data retention: {WINDOW_DAYS} days")
    print(f"Git push: {'enabled' if GIT_PUSH else 'disabled'}")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            take_reading(chan_ph, chan_tds)
            print("Sleeping for 30 minutes...")
            time.sleep(30 * 60)  # 30 minutes
            
    except KeyboardInterrupt:
        print("\nStopping sensor logger")
    except Exception as e:
        print(f"Daemon error: {e}")
        # Continue running despite errors
        time.sleep(60)  # Wait 1 minute before retrying


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Aquaponics sensor logger for Raspberry Pi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  WINDOW_DAYS=60     Days of data to retain (default: 60)
  ADS1115_ADDR=0x48  I2C address of ADS1115 (default: 0x48)
  ADC_CH_PH=0        ADS1115 channel for pH sensor (default: 0)  
  ADC_CH_TDS=1       ADS1115 channel for TDS sensor (default: 1)
  PH_SLOPE=-3.333    pH calibration slope (default: -3.333)
  PH_INTERCEPT=12.5  pH calibration intercept (default: 12.5)
  TDS_MULTIPLIER=0.5 TDS scaling factor (default: 0.5)
  GIT_PUSH=0         Enable git push after readings (default: 0)

Examples:
  python3 sensor_logger.py --once           # Take one reading
  python3 sensor_logger.py                  # Run daemon
  PH_SLOPE=0 python3 sensor_logger.py --once # Ignore pH sensor
        """
    )
    
    parser.add_argument(
        '--once', 
        action='store_true',
        help='Take one reading then exit (for testing)'
    )
    
    args = parser.parse_args()
    
    print("Aquaponics Sensor Logger")
    print("=" * 40)
    
    # Initialize hardware
    chan_ph, chan_tds = init_ads1115()
    
    if args.once:
        print("Taking single reading...")
        take_reading(chan_ph, chan_tds)
    else:
        run_daemon(chan_ph, chan_tds)


if __name__ == "__main__":
    main()