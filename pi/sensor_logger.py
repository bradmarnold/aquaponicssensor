#!/usr/bin/env python3
"""
sensor_logger.py - Raspberry Pi Aquaponics Sensor Logger
========================================================

Thin CLI wrapper for aquaponics sensor monitoring.
Uses modular sensor interface and data logger components.

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
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Import sensor modules
try:
    from .sensors import create_sensors_from_env
    from .logger import DataLogger
except ImportError:
    # Handle running as script
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from sensors import create_sensors_from_env
    from logger import DataLogger

# Configuration from environment
WINDOW_DAYS = int(os.getenv("WINDOW_DAYS", "60"))
GIT_PUSH = os.getenv("GIT_PUSH", "0") == "1"

# Data file path
DATA_FILE = Path(__file__).parent.parent / "data.json"


def take_reading() -> bool:
    """Take a single sensor reading and save to data file.
    
    Returns:
        True if reading successful, False otherwise
    """
    try:
        # Create sensors interface
        sensors = create_sensors_from_env()
        
        # Take reading
        reading = sensors.read_all()
        
        print(f"Reading: {reading}")
        
        # Save to data file
        data_logger = DataLogger(DATA_FILE, WINDOW_DAYS)
        success = data_logger.append_reading(reading)
        
        if success:
            # Get stats for logging
            stats = data_logger.get_data_stats()
            print(f"Saved {stats['total_readings']} readings to {DATA_FILE}")
            
            # Optional git push
            if GIT_PUSH:
                git_push_data()
        else:
            print("Failed to save reading")
            
        return success
        
    except Exception as e:
        print(f"Error taking reading: {e}")
        return False


def git_push_data():
    """Push data changes to git repository if configured."""
    if not GIT_PUSH:
        return
    
    try:
        repo_root = DATA_FILE.parent
        
        # Check if we're in a git repository
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print("Not in a git repository, skipping git push")
            return
        
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
        commit_msg = f"Sensor reading at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"Git commit: {commit_msg}")
        elif "nothing to commit" in result.stdout:
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


def run_daemon():
    """Run sensor logger as daemon with 30-minute intervals."""
    print("Aquaponics Sensor Logger")
    print("=" * 40)
    print("Running as daemon (30-minute intervals)")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        while True:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Taking reading...")
            
            success = take_reading()
            if not success:
                print("Reading failed, will retry in 30 minutes")
            
            print("Waiting 30 minutes for next reading...")
            time.sleep(30 * 60)  # 30 minutes
            
    except KeyboardInterrupt:
        print("\nStopping sensor logger")
    except Exception as e:
        print(f"Daemon error: {e}")
        sys.exit(1)

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
    
    parser.add_argument("--once", action="store_true",
                       help="Take one reading then exit (for testing)")
    
    args = parser.parse_args()
    
    if args.once:
        print("Aquaponics Sensor Logger")
        print("=" * 40)
        # Check for mock mode
        try:
            from . import create_sensors_from_env
            sensors = create_sensors_from_env()
            # Check if using mock hardware
            if hasattr(sensors.adc, 'mock_voltages') or hasattr(sensors.temp_sensor, 'mock_temp'):
                print("Warning: Running in mock mode - no hardware access")
        except:
            print("Warning: Adafruit libraries not available. Mock mode enabled.")
        
        print("Taking single reading...")
        success = take_reading()
        sys.exit(0 if success else 1)
    else:
        run_daemon()


if __name__ == "__main__":
    main()