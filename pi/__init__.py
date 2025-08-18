"""
Aquaponics Sensor Package
========================

Production-ready sensor monitoring for aquaponics systems.
Provides hardware abstraction, sensor interfaces, and data logging.
"""

from .hal import ADC, OneWireTemp, create_adc, create_temp_sensor
from .conversions import (
    ph_from_voltage,
    ec_from_voltage, 
    tds_from_ec,
    voltage_to_tds,
    voltage_to_ph,
    compensate_temperature,
    validate_sensor_range
)
from .sensors import AquaponicsSensors, create_sensors_from_env
from .logger import DataLogger, load_data_from_file, save_data_to_file, append_reading_to_file

__version__ = "1.0.0"
__author__ = "Aquaponics Monitoring System"

__all__ = [
    # Hardware abstraction
    "ADC",
    "OneWireTemp", 
    "create_adc",
    "create_temp_sensor",
    
    # Pure conversion functions
    "ph_from_voltage",
    "ec_from_voltage",
    "tds_from_ec", 
    "voltage_to_tds",
    "voltage_to_ph",
    "compensate_temperature",
    "validate_sensor_range",
    
    # High-level sensor interface
    "AquaponicsSensors",
    "create_sensors_from_env",
    
    # Data management
    "DataLogger",
    "load_data_from_file",
    "save_data_to_file", 
    "append_reading_to_file",
]