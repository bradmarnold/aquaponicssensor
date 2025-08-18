# Aquaponics Monitoring System

A production-ready, privacy-conscious aquaponics monitoring system for Raspberry Pi 4. Logs pH, TDS, and water temperature using DFRobot sensors, stores data locally with configurable retention, and provides a beautiful web dashboard with AI-powered coaching advice.

## Features

- **Sensor Monitoring**: pH, TDS (Total Dissolved Solids), and water temperature
- **Professional Hardware**: DFRobot Gravity sensor ecosystem with ADS1115 ADC
- **Configurable Data Retention**: Rolling window (default 60 days) with automatic pruning
- **Beautiful Dashboard**: Six interactive Chart.js visualizations in light mode
- **AI Water Coach**: OpenAI-powered insights and recommendations via Structured Outputs
- **Privacy-Conscious**: All data stored locally, optional cloud sync
- **Production Ready**: Defensive error handling, environment-driven configuration
- **GitHub Integration**: Automatic data commits and GitHub Pages hosting

## Hardware Requirements

| Component | Description | Connection |
|-----------|-------------|------------|
| **pH Sensor** | DFRobot Gravity pH Kit V2 (SEN0161-V2) | ADS1115 → A0 |
| **TDS Sensor** | DFRobot Gravity TDS Sensor (SEN0244) | ADS1115 → A1 |
| **Temperature** | DS18B20 waterproof probe (DFR0198) | GPIO4 + 4.7kΩ pull-up |
| **ADC** | ADS1115 16-bit I²C module (DFR0553) | I²C (SDA=GPIO2, SCL=GPIO3) |
| **Computer** | Raspberry Pi 4 Model B (4GB) | 5V 3A USB-C power |

### Wiring Overview
```
ADS1115:  VCC→3.3V, GND→GND, SDA→GPIO2, SCL→GPIO3
pH:       Red→VCC, Black→GND, Blue→ADS1115 A0  
TDS:      Red→VCC, Black→GND, Yellow→ADS1115 A1
DS18B20:  Red→3.3V, Black→GND, Yellow→GPIO4 (+ 4.7kΩ to 3.3V)
```

## Quick Start

### 1. Hardware Setup
See [docs/Pi_Wiring_and_Setup.txt](docs/Pi_Wiring_and_Setup.txt) for detailed wiring diagrams and Pi configuration.

### 2. Software Installation
```bash
# Enable I²C and 1-Wire in raspi-config
sudo raspi-config  # Interface Options → I2C & 1-Wire → Enable

# Clone repository
git clone https://github.com/your-username/aquaponicssensor.git
cd aquaponicssensor

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r pi/requirements.txt
```

### 3. Test Hardware
```bash
# Test single reading
cd pi
python3 sensor_logger.py --once

# Expected output:
# Reading: {'timestamp': '2024-01-15T10:30:00Z', 'ph': None, 'tds': 245.3, 'temp_c': 24.1}
```

### 4. Generate Seed Data (Optional)
```bash
# Create 60 days of zero-valued data for chart seeding
cd scripts
python3 generate_dummy_data.py --days 60 --zeros
```

### 5. Set Up Monitoring
```bash
# Add to crontab for 30-minute intervals
crontab -e

# Before pH calibration (ignore pH readings):
*/30 * * * * cd /home/pi/aquaponicssensor && PH_SLOPE=0 PH_INTERCEPT=0 WINDOW_DAYS=60 /home/pi/aquaponicssensor/venv/bin/python /home/pi/aquaponicssensor/pi/sensor_logger.py --once

# After calibration (full monitoring with git push):
*/30 * * * * cd /home/pi/aquaponicssensor && WINDOW_DAYS=60 PH_SLOPE=-3.333 PH_INTERCEPT=12.5 TDS_MULTIPLIER=0.5 GIT_PUSH=1 /home/pi/aquaponicssensor/venv/bin/python /home/pi/aquaponicssensor/pi/sensor_logger.py --once
```

## Repository Structure

```
aquaponicssensor/
├── index.html                 # Dashboard with 6 charts + coach panel
├── data.json                  # Time series data (UTC timestamps)
├── coach.json                 # AI coaching advice (generated)
├── README.md                  # This file
├── requirements.txt           # Python dependencies
├── docs/
│   ├── Pi_Wiring_and_Setup.txt    # Hardware setup guide
│   └── Connect_Pi_and_Repo.txt    # Network & GitHub setup
├── pi/
│   ├── sensor_logger.py       # Raspberry Pi sensor logger
│   ├── coach.py               # AI coach generator (OpenAI)
│   └── requirements.txt       # Pi-specific dependencies
└── scripts/
    └── generate_dummy_data.py # Utility to create test data
```

## Dashboard Features

### Six Interactive Charts
- **Last 7 Days (Raw)**: pH, TDS (ppm), Temperature (°C)
- **Last 30 Days (Daily Averages)**: pH, TDS (ppm), Temperature (°C)
- **Fixed Height Containers**: Prevents resize loops and ensures stable layout
- **Zero-to-Null Mapping**: Seeded zero values ignored for clean charts
- **Auto-Refresh**: Every 30 minutes to match logging cadence

### Water Coach Panel
- **AI-Powered Insights**: Uses OpenAI Responses API with Structured Outputs
- **Smart Fallback**: Tries `coach.json` first, falls back to Vercel endpoint
- **Status Indicators**: OK (green), Watch (yellow), Alert (red)
- **Actionable Advice**: Up to 3 metric-specific recommendations

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WINDOW_DAYS` | 60 | Days of data to retain |
| `ADS1115_ADDR` | 0x48 | I²C address of ADS1115 |
| `ADC_CH_PH` | 0 | ADS1115 channel for pH sensor |
| `ADC_CH_TDS` | 1 | ADS1115 channel for TDS sensor |
| `PH_SLOPE` | -3.333 | pH calibration slope |
| `PH_INTERCEPT` | 12.5 | pH calibration intercept |
| `TDS_MULTIPLIER` | 0.5 | TDS scaling factor (NaCl) |
| `GIT_PUSH` | 0 | Enable git commits (1=yes) |
| `OPENAI_API_KEY` | - | OpenAI API key for coaching |
| `OPENAI_MODEL` | gpt-4o-mini | OpenAI model to use |

### Pre-Calibration Setup
Before sensors arrive or during calibration:
```bash
# Disable pH readings while calibrating
export PH_SLOPE=0
export PH_INTERCEPT=0
```

## Calibration Procedures

### pH Sensor (Two-Point Calibration)
1. **Measure buffer solutions**:
   - pH 7.00 buffer → record voltage V1
   - pH 4.00 buffer → record voltage V2

2. **Calculate calibration constants**:
   ```
   PH_SLOPE = (7.00 - 4.00) / (V1 - V2)
   PH_INTERCEPT = 7.00 - PH_SLOPE * V1
   ```

3. **Update environment variables**:
   ```bash
   export PH_SLOPE=-3.333    # Your calculated value
   export PH_INTERCEPT=12.5  # Your calculated value
   ```

### TDS Sensor Calibration
1. **Choose reference standard**:
   - 1413 µS/cm EC solution, or
   - 342 ppm NaCl solution

2. **Measure and adjust**:
   ```bash
   # If measuring 400 ppm when solution is 342 ppm:
   NEW_MULTIPLIER = 0.5 × (342/400) = 0.428
   export TDS_MULTIPLIER=0.428
   ```

## GitHub Pages Setup

### Enable GitHub Pages
1. Go to repository Settings → Pages
2. Source: "Deploy from a branch"  
3. Branch: "main", Folder: "/ (root)"
4. Dashboard available at: `https://your-username.github.io/aquaponicssensor/`

### Automatic Updates
With `GIT_PUSH=1`, the sensor logger automatically:
1. Takes readings every 30 minutes
2. Updates `data.json`
3. Commits and pushes changes
4. Triggers GitHub Pages rebuild
5. Dashboard updates within 2 minutes

### Hard Refresh
GitHub Pages caches aggressively. For immediate updates:
- Add query parameter: `?t=123456`
- Use browser hard refresh: Ctrl+Shift+R

## AI Coach Setup

### OpenAI Configuration
```bash
# Required for coach functionality
export OPENAI_API_KEY="your-openai-api-key"
export OPENAI_MODEL="gpt-4o-mini"  # Optional, default shown
```

### Generate Coaching Advice
```bash
cd pi
python3 coach.py
# Creates ../coach.json with structured insights
```

### Vercel Fallback (Optional)
For serverless coaching, deploy Vercel function at `/api/coach` that:
1. Fetches data.json from GitHub
2. Calls OpenAI with same schema
3. Returns JSON with CORS headers

## Security & Privacy

### Data Privacy
- **Local Storage**: All sensor data stored on Pi and repository
- **No Cloud Dependency**: System works completely offline
- **Optional Sync**: GitHub integration is optional
- **API Key Security**: OpenAI key never committed or logged

### Security Best Practices
- Keep `OPENAI_API_KEY` on Pi only (never commit)
- Use environment variables or `.env` files
- Enable Pi firewall: `sudo ufw enable`
- Change default passwords
- Use SSH keys for GitHub authentication

## Troubleshooting

### Common Issues

**"No module named 'board'" error:**
- Ensure running on Raspberry Pi with Blinka
- Check virtual environment is activated

**I²C device not found:**
- Verify I²C enabled: `sudo raspi-config`
- Test with: `i2cdetect -y 1`
- Check wiring connections

**DS18B20 not found:**
- Verify 1-Wire enabled: `sudo raspi-config`  
- Check pull-up resistor (4.7kΩ)
- Test with: `ls /sys/bus/w1/devices/`

**pH readings always None:**
- Check `PH_SLOPE` and `PH_INTERCEPT` values
- For testing: Set `PH_SLOPE=0` to disable

**Charts show flat lines:**
- Zero values mapped to null (expected for seed data)
- Generate realistic test data: `scripts/generate_dummy_data.py --realistic`

### Getting Help

1. Check hardware connections against wiring diagrams
2. Review logs: `journalctl -u your-service-name`
3. Test individual components with `--once` flag
4. See detailed setup guides in `docs/` folder

## Development & Contributing

### Project Goals
- **Minimal Dependencies**: Pure Python, static HTML, no build steps
- **Defensive Coding**: Handle sensor failures gracefully
- **Clear Documentation**: Comprehensive setup guides
- **Production Ready**: 24/7 reliability for real aquaponics systems

### File Modification Guidelines
- **sensor_logger.py**: Modify for different sensors or logging logic
- **coach.py**: Adjust prompt or OpenAI parameters for better insights
- **index.html**: Customize dashboard appearance or add charts
- **generate_dummy_data.py**: Create different test data patterns

### Testing
```bash
# Complete setup with testing infrastructure
make setup

# Test sensor reading
python3 pi/sensor_logger.py --once

# Test coaching
python3 pi/coach.py

# Generate test data
python3 scripts/generate_dummy_data.py --realistic --days 7

# Serve dashboard locally
make serve
# Visit: http://localhost:8000

# Run all tests
make test

# Run end-to-end tests
make e2e

# Run all quality checks
make check
```

### Development Infrastructure

This project includes comprehensive development infrastructure:

- **103 Unit Tests**: Comprehensive test suite covering all modules
- **E2E Tests**: Playwright tests for dashboard functionality
- **CI/CD Pipeline**: 8-job GitHub Actions workflow
- **Code Quality**: Ruff linting, Black formatting, MyPy type checking
- **Pre-commit Hooks**: Automated code quality enforcement
- **JSON Schema Validation**: Data integrity guarantees
- **Development Server**: Local testing with proper MIME types
- **Makefile**: Streamlined development commands

### Production Deployment

For production deployment on Raspberry Pi:

1. **Hardware Setup**: Follow `docs/Pi_Wiring_and_Setup.txt`
2. **Network Setup**: Follow `docs/Connect_Pi_and_Repo.txt`
3. **Testing**: Run `make sensor-test` to verify sensors
4. **Data Generation**: Use `make data` to create sample data
5. **Monitoring**: Enable cron job for automatic readings
6. **Dashboard**: Deploy via GitHub Pages or local server

## License

MIT License - see LICENSE file for details.

## Support

For hardware setup questions, see detailed guides in `docs/` folder.
For software issues, check troubleshooting section above.

---

**Built for real aquaponics systems. Privacy-conscious. Production-ready.**