#!/usr/bin/env python3
"""
sensor_logger.py - Raspberry Pi Aquaponics Sensor Logger
========================================================

Takes a reading via sensors.create_sensors_from_env(), appends to data.json,
prunes to a rolling WINDOW_DAYS, and (optionally) git-pushes.

Env:
  WINDOW_DAYS=60
  GIT_PUSH=0|1
"""

from __future__ import annotations
import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Import sensor modules (works if run as script or package)
try:
    from .sensors import create_sensors_from_env
    from .logger import DataLogger
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from sensors import create_sensors_from_env
    from logger import DataLogger

# Config
WINDOW_DAYS = int(os.getenv("WINDOW_DAYS", "60"))
GIT_PUSH = os.getenv("GIT_PUSH", "0") == "1"

# Paths
REPO_ROOT = Path(__file__).parent.parent
DATA_FILE = REPO_ROOT / "data.json"


def git_push_data() -> None:
    """Push data changes to git repository if configured."""
    if not GIT_PUSH:
        return
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            print("Not in a git repository, skipping git push")
            return

        subprocess.run(["git", "add", "data.json"], cwd=REPO_ROOT, check=False)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        commit = subprocess.run(
            ["git", "commit", "-m", f"chore: sensor reading {ts}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if commit.returncode != 0 and "nothing to commit" in (commit.stdout + commit.stderr):
            print("No changes to commit")
            return

        push = subprocess.run(
            ["git", "push"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if push.returncode != 0:
            print(f"Git push failed: {push.stderr.strip()}")
        else:
            print("Successfully pushed data to git repository")

    except subprocess.TimeoutExpired:
        print("Git operation timed out")
    except Exception as e:
        print(f"Error during git push: {e}")


def take_reading() -> bool:
    """Take a single sensor reading and save to data file."""
    try:
        sensors = create_sensors_from_env()
        reading = sensors.read_all()  # should be {'timestamp', 'ph', 'tds', 'temp_c'}
        print(f"Reading: {reading}")

        logger = DataLogger(DATA_FILE, WINDOW_DAYS)
        ok = logger.append_reading(reading)
        if ok:
            stats = logger.get_data_stats()
            print(f"Saved {stats['total_readings']} readings to {DATA_FILE}")
            if GIT_PUSH:
                git_push_data()
        else:
            print("Failed to save reading")
        return ok

    except Exception as e:
        print(f"Error taking reading: {e}")
        return False


def run_daemon(interval_minutes: int = 30) -> None:
    print("Aquaponics Sensor Logger")
    print("=" * 40)
    print(f"Running as daemon ({interval_minutes}-minute intervals)")
    print("Press Ctrl+C to stop\n")
    try:
        while True:
            print(f"[{datetime.now(timezone.utc).isoformat()}] Taking reading...")
            ok = take_reading()
            if not ok:
                print("Reading failed, will retry next cycle")
            print(f"Waiting {interval_minutes} minutes for next reading...")
            time.sleep(interval_minutes * 60)
    except KeyboardInterrupt:
        print("\nStopping sensor logger")
    except Exception as e:
        print(f"Daemon error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Aquaponics sensor logger for Raspberry Pi"
    )
    parser.add_argument("--once", action="store_true",
                        help="Take one reading then exit")
    parser.add_argument("--interval", type=int, default=int(os.getenv("LOG_INTERVAL_MIN", "30")),
                        help="Daemon interval minutes (default: 30)")
    args = parser.parse_args()

    if args.once:
        print("Aquaponics Sensor Logger")
        print("=" * 40)
        print("Taking single reading...")
        ok = take_reading()
        sys.exit(0 if ok else 1)
    else:
        run_daemon(args.interval)


if __name__ == "__main__":
    main()
