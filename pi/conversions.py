"""
Pure Mathematical Conversions for Aquaponics Sensors
====================================================

Contains pure functions for converting sensor voltages to physical measurements.
All functions are stateless and testable without hardware dependencies.
"""

import math
from typing import Optional


def ph_from_voltage(voltage: float, slope: float, intercept: float) -> Optional[float]:
    """Convert pH sensor voltage to pH value using linear calibration.
    
    pH sensors typically have a linear response with voltage.
    Standard calibration uses two-point calibration with pH 4.0 and pH 7.0 buffers.
    
    Args:
        voltage: Sensor voltage in volts (0.0-5.0V)
        slope: Calibration slope (typically negative, around -3.33 for most sensors)
        intercept: Calibration intercept (typically around 12.5)
        
    Returns:
        pH value (0.0-14.0), or None if invalid inputs
        
    Example:
        # Typical DFRobot pH sensor calibration
        ph = ph_from_voltage(2.5, -3.333, 12.5)  # → ~7.0
    """
    if voltage is None:
        return None
    
    # Validate input ranges
    if not (0.0 <= voltage <= 5.0):
        return None
    
    # Skip conversion if slope is 0 (sensor not calibrated yet)
    if slope == 0:
        return None
    
    # Linear conversion: pH = slope * voltage + intercept
    ph = slope * voltage + intercept
    
    # Guard against implausible pH values
    if not (0.0 <= ph <= 14.0):
        return None
    
    return round(ph, 3)


def ec_from_voltage(voltage: float, temp_c: float) -> Optional[float]:
    """Convert TDS sensor voltage to electrical conductivity with temperature compensation.
    
    Uses DFRobot TDS sensor polynomial with temperature compensation to 25°C reference.
    The polynomial is calibrated for the specific sensor characteristics.
    
    Args:
        voltage: TDS sensor voltage in volts (0.0-5.0V)
        temp_c: Water temperature in Celsius for compensation
        
    Returns:
        Electrical conductivity in µS/cm, or None if invalid inputs
        
    Notes:
        - Temperature compensation assumes ~2%/°C coefficient
        - Polynomial is specific to DFRobot TDS sensor (SEN0244)
        - Reference temperature is 25°C
    """
    if voltage is None or temp_c is None:
        return None
    
    # Validate input ranges
    if not (0.0 <= voltage <= 5.0) or not (-10.0 <= temp_c <= 60.0):
        return None
    
    try:
        # Temperature compensation (25°C reference)
        # Standard coefficient is ~2%/°C for most aqueous solutions
        compensation_coefficient = 1.0 + 0.02 * (temp_c - 25.0)
        
        # Ensure coefficient is positive
        if compensation_coefficient <= 0:
            compensation_coefficient = 1.0
        
        # Apply temperature compensation
        compensation_voltage = voltage / compensation_coefficient
        
        # DFRobot polynomial for EC (µS/cm)
        # Coefficients determined by manufacturer calibration
        ec = (
            133.42 * compensation_voltage ** 3
            - 255.86 * compensation_voltage ** 2
            + 857.39 * compensation_voltage
        )
        
        # Clamp negative values to zero
        ec = max(ec, 0.0)
        
        return ec
        
    except (ValueError, ZeroDivisionError):
        return None


def tds_from_ec(ec_uS_cm: float, multiplier: float = 0.5) -> Optional[float]:
    """Convert electrical conductivity to Total Dissolved Solids (TDS).
    
    TDS is estimated from EC using an empirical conversion factor.
    The multiplier depends on the type of dissolved solids.
    
    Args:
        ec_uS_cm: Electrical conductivity in µS/cm
        multiplier: Conversion factor (0.5 for NaCl, 0.6-0.7 for mixed solutions)
        
    Returns:
        TDS in ppm (parts per million), or None if invalid inputs
        
    Notes:
        - 0.5 multiplier is standard for NaCl solutions
        - 0.6-0.7 multiplier more accurate for natural waters
        - Actual relationship varies with ion composition
    """
    if ec_uS_cm is None:
        return None
    
    # Validate inputs
    if ec_uS_cm < 0 or multiplier <= 0:
        return None
    
    try:
        tds = ec_uS_cm * multiplier
        
        # Guard against implausible TDS values (0-5000 ppm range for aquaponics)
        if tds > 5000:
            return None
        
        return round(tds, 1)
        
    except (ValueError, TypeError):
        return None


def voltage_to_tds(voltage: float, temp_c: float, multiplier: float = 0.5) -> Optional[float]:
    """Convert TDS sensor voltage directly to TDS in ppm.
    
    Convenience function that combines EC calculation and TDS conversion.
    
    Args:
        voltage: TDS sensor voltage in volts
        temp_c: Water temperature in Celsius
        multiplier: TDS conversion factor
        
    Returns:
        TDS in ppm, or None if invalid inputs
    """
    ec = ec_from_voltage(voltage, temp_c)
    if ec is None:
        return None
    
    return tds_from_ec(ec, multiplier)


def voltage_to_ph(voltage: float, slope: float, intercept: float) -> Optional[float]:
    """Convert pH sensor voltage directly to pH value.
    
    Convenience function that wraps ph_from_voltage with the same interface.
    
    Args:
        voltage: pH sensor voltage in volts
        slope: Calibration slope
        intercept: Calibration intercept
        
    Returns:
        pH value, or None if invalid inputs
    """
    return ph_from_voltage(voltage, slope, intercept)


def compensate_temperature(value: float, temp_c: float, reference_temp: float = 25.0, 
                          coefficient: float = 0.02) -> float:
    """Apply temperature compensation to a measurement.
    
    Generic temperature compensation function for any measurement that
    has a linear temperature dependence.
    
    Args:
        value: Measurement value to compensate
        temp_c: Current temperature in Celsius
        reference_temp: Reference temperature (default 25°C)
        coefficient: Temperature coefficient (default 2%/°C = 0.02)
        
    Returns:
        Temperature-compensated value
    """
    if temp_c is None or value is None:
        return value
    
    # Calculate compensation factor
    temp_diff = temp_c - reference_temp
    compensation_factor = 1.0 + coefficient * temp_diff
    
    # Ensure factor is positive
    if compensation_factor <= 0:
        compensation_factor = 1.0
    
    return value / compensation_factor


def validate_sensor_range(value: float, min_val: float, max_val: float, 
                         name: str = "sensor") -> bool:
    """Validate that a sensor reading is within expected range.
    
    Args:
        value: Sensor reading to validate
        min_val: Minimum expected value
        max_val: Maximum expected value  
        name: Sensor name for logging
        
    Returns:
        True if value is within range, False otherwise
    """
    if value is None:
        return False
    
    if not isinstance(value, (int, float)):
        return False
    
    if math.isnan(value) or math.isinf(value):
        return False
    
    return min_val <= value <= max_val