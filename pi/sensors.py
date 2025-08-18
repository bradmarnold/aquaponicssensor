"""
High-level Sensor Interface for Aquaponics Monitoring
=====================================================

Provides a clean interface for reading pH, TDS, and temperature sensors.
Uses the Hardware Abstraction Layer (HAL) and pure conversion functions.
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

try:
    from .hal import create_adc, create_temp_sensor, ADC, OneWireTemp
    from .conversions import voltage_to_ph, voltage_to_tds, validate_sensor_range
except ImportError:
    # Handle running as script
    from hal import create_adc, create_temp_sensor, ADC, OneWireTemp
    from conversions import voltage_to_ph, voltage_to_tds, validate_sensor_range


class AquaponicsSensors:
    """High-level interface for aquaponics sensor readings."""
    
    def __init__(self, 
                 adc_address: int = 0x48,
                 ph_channel: int = 0,
                 tds_channel: int = 1,
                 ph_slope: float = -3.333,
                 ph_intercept: float = 12.5,
                 tds_multiplier: float = 0.5,
                 mock: bool = False):
        """Initialize sensor interface.
        
        Args:
            adc_address: I2C address of ADS1115 ADC
            ph_channel: ADC channel for pH sensor (0-3)
            tds_channel: ADC channel for TDS sensor (0-3)
            ph_slope: pH calibration slope
            ph_intercept: pH calibration intercept
            tds_multiplier: TDS conversion multiplier
            mock: Use mock hardware for testing
        """
        self.adc_address = adc_address
        self.ph_channel = ph_channel
        self.tds_channel = tds_channel
        self.ph_slope = ph_slope
        self.ph_intercept = ph_intercept
        self.tds_multiplier = tds_multiplier
        
        # Initialize hardware interfaces
        self.adc: ADC = create_adc(adc_address, mock=mock)
        self.temp_sensor: OneWireTemp = create_temp_sensor(mock=mock)
        
        # Sensor validation ranges
        self.ph_range = (0.0, 14.0)
        self.tds_range = (0.0, 5000.0)  # ppm
        self.temp_range = (-10.0, 60.0)  # Celsius
    
    def read_ph(self) -> Optional[float]:
        """Read pH value from sensor.
        
        Returns:
            pH value (0.0-14.0), or None if reading failed
        """
        try:
            voltage = self.adc.read_voltage(self.ph_channel)
            ph = voltage_to_ph(voltage, self.ph_slope, self.ph_intercept)
            
            if ph is not None and validate_sensor_range(ph, *self.ph_range, "pH"):
                return ph
            
            return None
            
        except Exception as e:
            print(f"Error reading pH sensor: {e}")
            return None
    
    def read_temperature(self) -> Optional[float]:
        """Read water temperature from DS18B20 sensor.
        
        Returns:
            Temperature in Celsius, or None if reading failed
        """
        try:
            temp_c = self.temp_sensor.read_celsius()
            
            if temp_c is not None and validate_sensor_range(temp_c, *self.temp_range, "temperature"):
                return round(temp_c, 2)
            
            return None
            
        except Exception as e:
            print(f"Error reading temperature sensor: {e}")
            return None
    
    def read_tds(self, temp_c: Optional[float] = None) -> Optional[float]:
        """Read TDS value from sensor with temperature compensation.
        
        Args:
            temp_c: Water temperature for compensation. If None, reads from temp sensor.
            
        Returns:
            TDS in ppm, or None if reading failed
        """
        try:
            voltage = self.adc.read_voltage(self.tds_channel)
            
            # Get temperature for compensation
            if temp_c is None:
                temp_c = self.read_temperature()
            
            # Default to 25°C if no temperature available
            if temp_c is None:
                temp_c = 25.0
            
            tds = voltage_to_tds(voltage, temp_c, self.tds_multiplier)
            
            if tds is not None and validate_sensor_range(tds, *self.tds_range, "TDS"):
                return tds
            
            return None
            
        except Exception as e:
            print(f"Error reading TDS sensor: {e}")
            return None
    
    def read_all(self) -> Dict[str, Any]:
        """Read all sensors and return as structured data.
        
        Returns:
            Dictionary with timestamp and sensor readings
        """
        # Read temperature first for TDS compensation
        temp_c = self.read_temperature()
        
        # Read other sensors
        ph = self.read_ph()
        tds = self.read_tds(temp_c)
        
        # Create reading with UTC timestamp
        reading = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ph": ph,
            "tds": tds,
            "temp_c": temp_c
        }
        
        return reading
    
    def test_sensors(self) -> Dict[str, Any]:
        """Test all sensors and return diagnostic information.
        
        Returns:
            Dictionary with sensor test results and diagnostics
        """
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "adc_address": f"0x{self.adc_address:02x}",
            "channels": {
                "ph": self.ph_channel,
                "tds": self.tds_channel
            },
            "calibration": {
                "ph_slope": self.ph_slope,
                "ph_intercept": self.ph_intercept,
                "tds_multiplier": self.tds_multiplier
            },
            "sensors": {}
        }
        
        # Test pH sensor
        try:
            ph_voltage = self.adc.read_voltage(self.ph_channel)
            ph_value = self.read_ph()
            results["sensors"]["ph"] = {
                "voltage": ph_voltage,
                "value": ph_value,
                "status": "ok" if ph_value is not None else "error"
            }
        except Exception as e:
            results["sensors"]["ph"] = {
                "voltage": None,
                "value": None,
                "status": f"error: {e}"
            }
        
        # Test temperature sensor
        try:
            temp_value = self.read_temperature()
            results["sensors"]["temperature"] = {
                "value": temp_value,
                "status": "ok" if temp_value is not None else "error"
            }
        except Exception as e:
            results["sensors"]["temperature"] = {
                "value": None,
                "status": f"error: {e}"
            }
        
        # Test TDS sensor
        try:
            tds_voltage = self.adc.read_voltage(self.tds_channel)
            tds_value = self.read_tds()
            results["sensors"]["tds"] = {
                "voltage": tds_voltage,
                "value": tds_value,
                "status": "ok" if tds_value is not None else "error"
            }
        except Exception as e:
            results["sensors"]["tds"] = {
                "voltage": None,
                "value": None,
                "status": f"error: {e}"
            }
        
        return results


def create_sensors_from_env() -> AquaponicsSensors:
    """Create sensor interface using environment variables.
    
    Environment variables:
        ADS1115_ADDR: I2C address (default: 0x48)
        ADC_CH_PH: pH sensor channel (default: 0)
        ADC_CH_TDS: TDS sensor channel (default: 1)
        PH_SLOPE: pH calibration slope (default: -3.333)
        PH_INTERCEPT: pH calibration intercept (default: 12.5)
        TDS_MULTIPLIER: TDS conversion factor (default: 0.5)
        MOCK_HARDWARE: Use mock sensors (default: 0)
    
    Returns:
        Configured AquaponicsSensors instance
    """
    # Parse environment variables with defaults
    adc_address = int(os.getenv("ADS1115_ADDR", "0x48"), 16)
    ph_channel = int(os.getenv("ADC_CH_PH", "0"))
    tds_channel = int(os.getenv("ADC_CH_TDS", "1"))
    ph_slope = float(os.getenv("PH_SLOPE", "-3.333"))
    ph_intercept = float(os.getenv("PH_INTERCEPT", "12.5"))
    tds_multiplier = float(os.getenv("TDS_MULTIPLIER", "0.5"))
    mock = os.getenv("MOCK_HARDWARE", "0") == "1"
    
    return AquaponicsSensors(
        adc_address=adc_address,
        ph_channel=ph_channel,
        tds_channel=tds_channel,
        ph_slope=ph_slope,
        ph_intercept=ph_intercept,
        tds_multiplier=tds_multiplier,
        mock=mock
    )