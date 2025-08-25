#!/usr/bin/env python3
"""
sensors.py - Hardware access for aquaponics sensors

- pH via ADS1115 A0
- TDS via ADS1115 A1
- DS18B20 on GPIO4 (1-Wire)
- Calibration via env or config.json

Env (overrides config.json if present):
  ADS1115_ADDR=0x48
  ADC_CH_PH=0
  ADC_CH_TDS=1
  PH_M=-3.333
  PH_B=12.5
  TDS_SCALE=0.5           # ppm per millivolt (see note below)
  TDS_ALPHA=0.02          # temperature coefficient per °C for compensation

Config file (optional): ../config.json
  {
    "ph":  { "m": -3.333, "b": 12.5 },
    "tds": { "scale": 0.5, "alpha": 0.02 }
  }

Notes:
- TDS_SCALE is interpreted as ppm per mV after calibration.
  Example: if 1.000 V should read ~500 ppm, SCALE ≈ 0.5 ppm/mV.
- Temperature compensation uses EC25 ≈ EC / (1 + alpha*(T-25)).
"""

from __future__ import annotations
import json
import os
import glob
from datetime import datetime, timezone
from pathlib import Path

# Try hardware libs; fall back to mock ONLY on ImportError
USE_MOCK = False
try:
    import board, busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
except ImportError:
    USE_MOCK = True


REPO_ROOT = Path(__file__).parent.parent
CONFIG_FILE = REPO_ROOT / "config.json"

# ---------- Helpers ----------

def _load_config():
    cfg = {}
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f) or {}
    except Exception as e:
        print(f"Warning: failed to read {CONFIG_FILE}: {e}")
    return cfg

def _get_env_or_cfg(cfg, path, default=None):
    """
    Lookup with env override. `path` like 'ph.m' or 'tds.scale'.
    """
    # Env overrides for well-known keys
    if path == "ph.m":
        v = os.getenv("PH_M", os.getenv("PH_SLOPE", None))
        if v is not None: return float(v)
    if path == "ph.b":
        v = os.getenv("PH_B", os.getenv("PH_INTERCEPT", None))
        if v is not None: return float(v)
    if path == "tds.scale":
        v = os.getenv("TDS_SCALE", os.getenv("TDS_MULTIPLIER", None))
        if v is not None: return float(v)
    if path == "tds.alpha":
        v = os.getenv("TDS_ALPHA", None)
        if v is not None: return float(v)

    # From config.json
    cur = cfg
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur

def _read_ds18b20_temp_c() -> float | None:
    # Find first DS18B20 device
    try:
        for dev in glob.glob("/sys/bus/w1/devices/28-*/w1_slave"):
            with open(dev, "r") as f:
                lines = f.read().strip().splitlines()
            if len(lines) >= 2 and lines[0].endswith("YES"):
                # ... t=24500
                idx = lines[1].find("t=")
                if idx != -1:
                    t_milli = int(lines[1][idx+2:])
                    return round(t_milli / 1000.0, 2)
    except Exception as e:
        print(f"Warning: DS18B20 read failed: {e}")
    return None

# ---------- Core class ----------

class Sensors:
    def __init__(self):
        self.cfg = _load_config()

        # Channels
        self.adc_addr = int(os.getenv("ADS1115_ADDR", "0x48"), 16)
        ch_ph  = int(os.getenv("ADC_CH_PH", "0"))
        ch_tds = int(os.getenv("ADC_CH_TDS", "1"))
        self.CH_MAP = None

        # Calibration
        self.ph_m = float(_get_env_or_cfg(self.cfg, "ph.m",  -3.333))  # rough default
        self.ph_b = float(_get_env_or_cfg(self.cfg, "ph.b",   12.5))
        self.tds_scale = float(_get_env_or_cfg(self.cfg, "tds.scale", 0.5))
        self.tds_alpha = float(_get_env_or_cfg(self.cfg, "tds.alpha", 0.02))

        self.temp_c = None

        # Hardware init
        self.use_mock = USE_MOCK
        if not self.use_mock:
            try:
                self.i2c = busio.I2C(board.SCL, board.SDA)
                self.ads = ADS.ADS1115(self.i2c, address=self.adc_addr)
                self.CH_MAP = {0: ADS.P0, 1: ADS.P1, 2: ADS.P2, 3: ADS.P3}
                self.ch_ph  = AnalogIn(self.ads, self.CH_MAP[ch_ph])
                self.ch_tds = AnalogIn(self.ads, self.CH_MAP[ch_tds])
            except Exception as e:
                print(f"Warning: ADS1115 init failed ({e}). Using mock mode.")
                self.use_mock = True

        # Mock voltages if needed
        if self.use_mock:
            self.mock_ph_v  = 1.65   # ~mid-scale
            self.mock_tds_v = 1.00
            print("Warning: Using mock sensor values (no hardware)")

    # ----- Reads -----

    def read_ph_voltage(self) -> float | None:
        try:
            return round(self.ch_ph.voltage, 4) if not self.use_mock else self.mock_ph_v
        except Exception as e:
            print(f"Error reading pH voltage: {e}")
            return None

    def read_tds_voltage(self) -> float | None:
        try:
            return round(self.ch_tds.voltage, 4) if not self.use_mock else self.mock_tds_v
        except Exception as e:
            print(f"Error reading TDS voltage: {e}")
            return None

    def read_temp_c(self) -> float | None:
        self.temp_c = _read_ds18b20_temp_c()
        return self.temp_c

    # ----- Calibration / conversion -----

    def ph_from_voltage(self, v: float | None) -> float | None:
        if v is None:
            return None
        # linear: pH = m*V + b
        return round(self.ph_m * v + self.ph_b, 2)

    def tds_from_voltage(self, v: float | None, temp_c: float | None) -> float | None:
        if v is None:
            return None
        # basic proportional model with temp compensation to 25°C
        # ppm_raw = (V * 1000 mV) * scale
        ppm_raw = max(0.0, v) * 1000.0 * self.tds_scale
        if temp_c is None:
            return round(ppm_raw, 2)
        comp = 1.0 + self.tds_alpha * (temp_c - 25.0)
        ppm_25 = ppm_raw / comp
        return round(ppm_25, 2)

    # ----- Public API -----

    def read_all(self) -> dict:
        ts = datetime.now(timezone.utc).isoformat()
        t  = self.read_temp_c()
        v_ph  = self.read_ph_voltage()
        v_tds = self.read_tds_voltage()
        ph  = self.ph_from_voltage(v_ph)
        tds = self.tds_from_voltage(v_tds, t)
        return {
            "timestamp": ts,
            "ph": ph,
            "tds": tds,
            "temp_c": t
        }


def create_sensors_from_env() -> Sensors:
    return Sensors()
