"""
sensor_logger.py
-----------------

This script runs on a Raspberry Pi and periodically samples pH, total dissolved solids (TDS) and
water temperature from sensors connected via an ADS1115 ADC and the 1‑Wire interface.  It stores
readings in a JSON file (`data.json`) and can optionally push updates to a GitHub repository for
remote viewing via GitHub Pages.

Prerequisites:

* The ADS1115 breakout wired to the Pi’s I²C pins.
* pH sensor analog output connected to channel 0 of the ADS1115.
* TDS sensor analog output connected to channel 1 of the ADS1115.
* DS18B20 temperature probe connected to GPIO 4 with a 4.7 kΩ pull‑up resistor.
* I²C and 1‑Wire interfaces enabled on the Pi.
* Python libraries listed in `requirements.txt` installed.

To enable GitHub syncing, set the following environment variables:

```
GITHUB_TOKEN  – Personal access token with repo scope
REPO_OWNER    – GitHub username or organisation
REPO_NAME     – Repository name (e.g. "aquaponics-monitor")
BRANCH_NAME   – Optional: branch to commit to (defaults to main)
FILE_PATH     – Optional: path of data file in repo (defaults to data.json)
```

When configured, each call to `push_to_github` will update the JSON file in the repository.

"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import schedule
import requests

try:
    import board
    import busio
    from adafruit_ads1x15.ads1115 import ADS1115
    from adafruit_ads1x15.analog_in import AnalogIn
except ImportError:
    # If running outside of Raspberry Pi or libraries not installed, allow import failure.
    ADS1115 = None  # type: ignore
    AnalogIn = None  # type: ignore


DATA_FILE = Path(__file__).with_name("data.json")


def init_ads1115():
    """Initialise the ADS1115 ADC and return channel objects for pH and TDS."""
    if ADS1115 is None:
        raise RuntimeError(
            "adafruit_ads1x15 library not available; ensure running on Raspberry Pi with Blinka"
        )
    i2c = busio.I2C(board.SCL, board.SDA)
    adc = ADS1115(i2c)
    # Use gain=1 for +/-4.096 V range (matches DFRobot sensors output up to 3 V)
    # Channels: A0 for pH, A1 for TDS
    chan_ph = AnalogIn(adc, ADS1115.P0)
    chan_tds = AnalogIn(adc, ADS1115.P1)
    return chan_ph, chan_tds


def read_ds18b20() -> float:
    """Read temperature from the first DS18B20 sensor on the 1‑Wire bus.

    Returns temperature in degrees Celsius.  Returns NaN if sensor not found or read fails.
    """
    base_dir = "/sys/bus/w1/devices"
    try:
        device_folder = next(
            (d for d in os.listdir(base_dir) if d.startswith("28-")), None
        )
        if not device_folder:
            return float("nan")
        device_file = Path(base_dir) / device_folder / "w1_slave"
        with open(device_file) as f:
            lines = f.read().splitlines()
        # Check CRC
        if lines[0].strip().split()[-1] != "YES":
            return float("nan")
        temp_str = lines[1].split("t=")[-1]
        return float(temp_str) / 1000.0
    except Exception:
        return float("nan")


def read_sensors(chan_ph, chan_tds) -> dict:
    """Read raw voltages from ADS1115 channels and convert to sensor values."""
    # Voltage in volts
    ph_voltage = chan_ph.voltage
    tds_voltage = chan_tds.voltage
    temp = read_ds18b20()

    # Convert voltages to pH and TDS using calibration constants.
    ph_value = voltage_to_ph(ph_voltage)
    tds_value = voltage_to_tds(tds_voltage, temp)

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "ph": round(ph_value, 3),
        "tds": round(tds_value, 1),  # in ppm
        "temp_c": round(temp, 2),
    }


def voltage_to_ph(voltage: float) -> float:
    """Convert raw pH sensor voltage to pH value.

    The DFRobot pH sensor outputs ~3.0 V at pH 7 and ~0.0 V at pH 0 (approximate).  For accurate
    results, perform a two‑point calibration using pH 4.0 and pH 7.0 buffer solutions and adjust
    the slope/intercept accordingly.
    """
    # Example calibration values: adjust after calibration
    # At pH7: 2.5 V, at pH4: 3.0 V (these are hypothetical; calibrate your sensor!)
    voltage_at_pH7 = 2.5
    voltage_at_pH4 = 3.0
    slope = (7.0 - 4.0) / (voltage_at_pH7 - voltage_at_pH4)
    intercept = 7.0 - slope * voltage_at_pH7
    return slope * voltage + intercept


def voltage_to_tds(voltage: float, temperature_c: float) -> float:
    """Convert raw TDS sensor voltage to ppm (parts per million).

    The DFRobot TDS sensor provides an example formula that compensates for temperature:

    ```python
    compensation_coefficient = 1.0 + 0.02 * (temperature_c - 25.0)
    compensation_voltage = voltage / compensation_coefficient
    tds_value = (133.42*V^3 - 255.86*V^2 + 857.39*V) * 0.5
    ```

    where V is the compensated voltage.  Adjust the polynomial coefficients based on calibration.
    """
    compensation_coefficient = 1.0 + 0.02 * (temperature_c - 25.0)
    if compensation_coefficient == 0:
        compensation_coefficient = 1.0
    compensation_voltage = voltage / compensation_coefficient
    tds = (
        133.42 * compensation_voltage ** 3
        - 255.86 * compensation_voltage ** 2
        + 857.39 * compensation_voltage
    ) * 0.5
    return max(tds, 0.0)


def load_data() -> list:
    """Load existing JSON data from file.  Returns an empty list if file does not exist."""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def prune_old_data(data: list, days: int = 7) -> list:
    """Keep only entries within the last `days` days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    pruned = []
    for entry in data:
        try:
            ts = datetime.fromisoformat(entry["timestamp"].rstrip("Z"))
            if ts >= cutoff:
                pruned.append(entry)
        except Exception:
            continue
    return pruned


def save_data(data: list) -> None:
    """Write data list to the JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def push_to_github():
    """Commit the updated data.json to GitHub using the REST API.

    Requires environment variables GITHUB_TOKEN, REPO_OWNER, REPO_NAME.  Optional variables:
    BRANCH_NAME (defaults to "main") and FILE_PATH (defaults to "data.json").
    """
    token = os.getenv("GITHUB_TOKEN")
    owner = os.getenv("REPO_OWNER")
    repo = os.getenv("REPO_NAME")
    branch = os.getenv("BRANCH_NAME", "main")
    filepath = os.getenv("FILE_PATH", "data.json")
    if not (token and owner and repo):
        print("GitHub credentials not fully configured; skipping push")
        return
    # Read current file content to compute SHA (if file exists)
    api_base = f"https://api.github.com/repos/{owner}/{repo}/contents/{filepath}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    # Get existing file SHA
    resp = requests.get(api_base, headers=headers, params={"ref": branch})
    sha = None
    if resp.status_code == 200:
        sha = resp.json().get("sha")
    with open(DATA_FILE, "rb") as f:
        content = f.read()
    import base64

    b64_content = base64.b64encode(content).decode("ascii")
    commit_message = f"Update {filepath} at {datetime.utcnow().isoformat()}"
    data = {
        "message": commit_message,
        "content": b64_content,
        "branch": branch,
    }
    if sha:
        data["sha"] = sha
    put_resp = requests.put(api_base, headers=headers, json=data)
    if put_resp.status_code in (201, 200):
        print(f"Pushed {filepath} to GitHub")
    else:
        print(f"Failed to push to GitHub: {put_resp.status_code}", put_resp.text)


def sample_and_log(chan_ph, chan_tds):
    """Take a sensor reading, append to data file, prune old entries and optionally push."""
    reading = read_sensors(chan_ph, chan_tds)
    print(f"Sampled data: {reading}")
    data = load_data()
    data.append(reading)
    # Remove entries older than 7 days
    data = prune_old_data(data, days=7)
    save_data(data)
    push_to_github()


def main():
    chan_ph, chan_tds = init_ads1115()
    # Take a reading immediately and then every 30 minutes
    sample_and_log(chan_ph, chan_tds)
    schedule.every(30).minutes.do(sample_and_log, chan_ph=chan_ph, chan_tds=chan_tds)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting logger")