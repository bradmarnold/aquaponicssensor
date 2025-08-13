# Aquaponics Monitoring System

This directory contains a Python-based sensor logger and a static web dashboard for monitoring an aquaponics system.  It collects data for pH, total dissolved solids (TDS) and water temperature using hardware connected to a Raspberry Pi, stores the data as JSON and optionally pushes updates to GitHub for live visualisation on GitHub Pages.  The dashboard plots the last seven days of readings and refreshes every 30 minutes.

## Contents

* **`sensor_logger.py`** – Reads analog values from a DFRobot pH sensor, TDS sensor and a DS18B20 temperature probe via an ADS1115 ADC and the Raspberry Pi’s 1‑Wire interface.  Converts raw voltages to physical units, appends new samples to `data.json` and (optionally) pushes updates to GitHub using a personal access token.
* **`data.json`** – Stores an array of timestamped sensor readings.  Each entry has ISO 8601 timestamp and values for pH, TDS (ppm) and temperature (°C).  This file is used by both the logger and the dashboard.
* **`index.html`** – A static dashboard built with Chart.js.  It fetches `data.json` from GitHub (or the same server) and renders interactive line charts for each parameter over the previous seven days.  The page automatically reloads data every 30 minutes.
* **`requirements.txt`** – Lists Python dependencies needed for the logger.

## Setup

### Hardware

You will need:

1. A Raspberry Pi (4 GB recommended) with Raspberry Pi OS installed.
2. An ADS1115 I²C ADC board wired to the Pi’s 3.3 V, GND, SDA (GPIO 2) and SCL (GPIO 3) pins.
3. DFRobot Gravity analog pH sensor kit connected to ADS1115 channel 0 (A0).
4. DFRobot Gravity analog TDS sensor connected to ADS1115 channel 1 (A1).
5. A waterproof DS18B20 temperature sensor wired to GPIO 4 with a 4.7 kΩ pull‑up resistor to 3.3 V.
6. Jumper wires and a breadboard to make the connections.

### Software

1. Enable I²C and 1‑Wire on the Pi via `sudo raspi-config`.
2. Install the required Python libraries:

   ```bash
   sudo apt update
   sudo apt install python3-pip python3-smbus i2c-tools
   pip3 install -r requirements.txt
   ```

3. Run the logger continuously (e.g. via `systemd` or a `tmux` session):

   ```bash
   python3 sensor_logger.py
   ```

4. Host `index.html` and `data.json` either using GitHub Pages or a local web server.  For GitHub Pages, push both files to the `gh-pages` branch of your repository.  The logger can be configured with a GitHub personal access token to commit `data.json` automatically.

## GitHub Integration

To enable automatic updates of `data.json` on GitHub:

1. Create a personal access token with `repo` scope from your GitHub account.
2. Set the `GITHUB_TOKEN`, `REPO_OWNER` and `REPO_NAME` environment variables on the Pi.  These are used by the logger to authenticate and push changes via the GitHub API.
3. When configured, the logger will commit the updated `data.json` to the default branch (or `gh-pages` if specified) every time a new sample is taken.

If you prefer not to use GitHub for data storage, simply serve `data.json` from the Pi directly (e.g. using `python3 -m http.server` or Flask) and adjust the URL in `index.html` accordingly.

## Calibration

Sensor calibration is critical for accurate readings.  Follow the manufacturer’s instructions to calibrate the pH and TDS sensors using buffer solutions.  Update the slope and intercept values in `sensor_logger.py` after calibration to convert voltages correctly.
