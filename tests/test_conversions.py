"""
Test conversions.py - Pure mathematical conversion functions
"""

import pytest
import math
import sys
from pathlib import Path

# Add pi module to path
sys.path.insert(0, str(Path(__file__).parent.parent / "pi"))

from conversions import (
    ph_from_voltage,
    ec_from_voltage,
    tds_from_ec,
    voltage_to_tds,
    voltage_to_ph,
    compensate_temperature,
    validate_sensor_range
)


class TestPHConversions:
    """Test pH voltage to pH value conversions."""
    
    def test_ph_from_voltage_basic(self):
        """Test basic pH conversion with standard calibration."""
        # Standard DFRobot calibration: slope=-3.333, intercept=12.5
        # pH = slope * voltage + intercept = -3.333 * V + 12.5
        # So for pH 7.0: 7.0 = -3.333 * V + 12.5 → V = (12.5 - 7.0) / 3.333 ≈ 1.65V
        # For pH 4.0: 4.0 = -3.333 * V + 12.5 → V = (12.5 - 4.0) / 3.333 ≈ 2.55V
        
        ph = ph_from_voltage(1.65, -3.333, 12.5)
        assert ph is not None
        assert 6.9 <= ph <= 7.1  # Allow small tolerance
        
        ph = ph_from_voltage(2.55, -3.333, 12.5)
        assert ph is not None
        assert 3.9 <= ph <= 4.1
    
    def test_ph_from_voltage_edge_cases(self):
        """Test pH conversion edge cases."""
        # Invalid voltage
        assert ph_from_voltage(None, -3.333, 12.5) is None
        assert ph_from_voltage(-1.0, -3.333, 12.5) is None
        assert ph_from_voltage(6.0, -3.333, 12.5) is None
        
        # Uncalibrated sensor (slope=0)
        assert ph_from_voltage(2.5, 0, 12.5) is None
        
        # Result outside pH range - these would give valid results within 0-14 range
        # pH = -3.333 * 0.0 + 12.5 = 12.5 (valid)
        # pH = -3.333 * 5.0 + 12.5 = -4.165 (invalid, outside 0-14 range)
        assert ph_from_voltage(5.0, -3.333, 12.5) is None  # Would give pH < 0
    
    def test_ph_precision(self):
        """Test pH value precision (3 decimal places)."""
        ph = ph_from_voltage(2.5, -3.333, 12.5)
        assert ph is not None
        # Should be rounded to 3 decimal places
        assert len(str(ph).split('.')[-1]) <= 3


class TestTDSConversions:
    """Test TDS voltage and EC conversions."""
    
    def test_ec_from_voltage_basic(self):
        """Test EC calculation from voltage."""
        # Test with standard conditions (25°C)
        ec = ec_from_voltage(1.8, 25.0)
        assert ec is not None
        assert ec >= 0
        
        # Higher voltage should give higher EC
        ec1 = ec_from_voltage(1.0, 25.0)
        ec2 = ec_from_voltage(2.0, 25.0)
        assert ec1 is not None and ec2 is not None
        assert ec2 > ec1
    
    def test_ec_temperature_compensation(self):
        """Test temperature compensation in EC calculation."""
        # Same voltage at different temperatures
        ec_cold = ec_from_voltage(2.0, 15.0)  # 15°C
        ec_ref = ec_from_voltage(2.0, 25.0)   # 25°C reference
        ec_warm = ec_from_voltage(2.0, 35.0)  # 35°C
        
        assert all(x is not None for x in [ec_cold, ec_ref, ec_warm])
        
        # Cold water should show higher EC (less compensation)
        # Warm water should show lower EC (more compensation)
        assert ec_cold > ec_ref > ec_warm
    
    def test_tds_from_ec(self):
        """Test TDS calculation from EC."""
        # Standard conversion with 0.5 multiplier
        tds = tds_from_ec(1000.0, 0.5)  # 1000 µS/cm
        assert tds == 500.0  # Should be 500 ppm
        
        # Different multiplier
        tds = tds_from_ec(1000.0, 0.7)
        assert tds == 700.0
        
        # Zero EC
        assert tds_from_ec(0.0, 0.5) == 0.0
        
        # Invalid inputs
        assert tds_from_ec(None, 0.5) is None
        assert tds_from_ec(1000.0, 0) is None
        assert tds_from_ec(-100.0, 0.5) is None
    
    def test_voltage_to_tds_integration(self):
        """Test full voltage to TDS conversion."""
        tds = voltage_to_tds(1.8, 22.5, 0.5)
        assert tds is not None
        assert tds >= 0
        assert tds < 5000  # Reasonable range
        
        # Invalid inputs
        assert voltage_to_tds(None, 22.5, 0.5) is None
        assert voltage_to_tds(1.8, None, 0.5) is None
        assert voltage_to_tds(-1.0, 22.5, 0.5) is None
        assert voltage_to_tds(1.8, -20.0, 0.5) is None


class TestTemperatureCompensation:
    """Test generic temperature compensation."""
    
    def test_compensate_temperature_basic(self):
        """Test basic temperature compensation."""
        # No compensation at reference temperature
        result = compensate_temperature(100.0, 25.0, 25.0, 0.02)
        assert result == 100.0
        
        # Compensation for higher temperature
        result = compensate_temperature(100.0, 35.0, 25.0, 0.02)
        assert result < 100.0  # Should be compensated down
        
        # Compensation for lower temperature  
        result = compensate_temperature(100.0, 15.0, 25.0, 0.02)
        assert result > 100.0  # Should be compensated up
    
    def test_compensate_temperature_edge_cases(self):
        """Test temperature compensation edge cases."""
        # None inputs
        assert compensate_temperature(None, 25.0) is None
        assert compensate_temperature(100.0, None) == 100.0
        
        # Extreme compensation that would make factor negative
        result = compensate_temperature(100.0, -100.0, 25.0, 0.02)
        assert result == 100.0  # Should default to 1.0 factor


class TestSensorValidation:
    """Test sensor range validation."""
    
    def test_validate_sensor_range_basic(self):
        """Test basic range validation."""
        assert validate_sensor_range(5.0, 0.0, 10.0) is True
        assert validate_sensor_range(0.0, 0.0, 10.0) is True
        assert validate_sensor_range(10.0, 0.0, 10.0) is True
        
        assert validate_sensor_range(-1.0, 0.0, 10.0) is False
        assert validate_sensor_range(11.0, 0.0, 10.0) is False
    
    def test_validate_sensor_range_invalid_inputs(self):
        """Test validation with invalid inputs."""
        assert validate_sensor_range(None, 0.0, 10.0) is False
        assert validate_sensor_range("invalid", 0.0, 10.0) is False
        assert validate_sensor_range(float('nan'), 0.0, 10.0) is False
        assert validate_sensor_range(float('inf'), 0.0, 10.0) is False


class TestConversionAccuracy:
    """Test conversion accuracy and realistic values."""
    
    def test_ph_realistic_values(self):
        """Test pH conversions with realistic sensor voltages."""
        # Typical voltage ranges for DFRobot pH sensor
        for voltage in [1.5, 2.0, 2.5, 3.0, 3.5]:
            ph = ph_from_voltage(voltage, -3.333, 12.5)
            if ph is not None:
                assert 0.0 <= ph <= 14.0
                assert isinstance(ph, float)
    
    def test_tds_realistic_values(self):
        """Test TDS conversions with realistic sensor voltages."""
        # Typical voltage ranges for TDS sensor
        temperatures = [18.0, 22.0, 25.0, 28.0, 32.0]
        voltages = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        
        for temp in temperatures:
            for voltage in voltages:
                tds = voltage_to_tds(voltage, temp, 0.5)
                if tds is not None:
                    assert 0.0 <= tds <= 5000.0
                    assert isinstance(tds, float)
                    # Check precision (1 decimal place)
                    assert len(str(tds).split('.')[-1]) <= 1
    
    def test_temperature_effects(self):
        """Test that temperature changes affect TDS readings appropriately."""
        base_voltage = 2.0
        temps = [15.0, 20.0, 25.0, 30.0, 35.0]
        
        tds_values = []
        for temp in temps:
            tds = voltage_to_tds(base_voltage, temp, 0.5)
            if tds is not None:
                tds_values.append(tds)
        
        # Should have different values due to temperature compensation
        assert len(set(tds_values)) > 1


if __name__ == "__main__":
    pytest.main([__file__])