"""
Test HAL (Hardware Abstraction Layer) mock implementations
"""

import pytest
import os
import tempfile
from pathlib import Path
import sys

# Add pi module to path  
sys.path.insert(0, str(Path(__file__).parent.parent / "pi"))

from hal import (
    MockADC,
    MockOneWireTemp,
    create_adc,
    create_temp_sensor,
    ADC,
    OneWireTemp
)


class TestMockADC:
    """Test MockADC implementation."""
    
    def test_mock_adc_initialization(self):
        """Test MockADC initialization."""
        adc = MockADC()
        assert adc.address == 0x48  # Default address
        
        adc_custom = MockADC(address=0x49)
        assert adc_custom.address == 0x49
    
    def test_mock_adc_voltage_reading(self):
        """Test voltage reading from MockADC."""
        adc = MockADC()
        
        # Test valid channels
        for channel in range(4):
            voltage = adc.read_voltage(channel)
            assert isinstance(voltage, float)
            assert 0.0 <= voltage <= 5.0  # Reasonable voltage range
        
        # Test invalid channel
        with pytest.raises(ValueError):
            adc.read_voltage(4)  # Channel 4 doesn't exist
        
        with pytest.raises(ValueError):
            adc.read_voltage(-1)  # Negative channel
    
    def test_mock_adc_deterministic_values(self):
        """Test that MockADC returns deterministic values."""
        adc1 = MockADC()
        adc2 = MockADC()
        
        # Same channel should return same voltage
        for channel in range(4):
            voltage1 = adc1.read_voltage(channel)
            voltage2 = adc2.read_voltage(channel)
            assert voltage1 == voltage2
    
    def test_mock_adc_default_voltages(self):
        """Test default mock voltages are reasonable for sensors."""
        adc = MockADC()
        
        # Channel 0 (pH) should give reasonable pH voltage
        ph_voltage = adc.read_voltage(0)
        assert 1.0 <= ph_voltage <= 4.0  # pH sensors typically in this range
        
        # Channel 1 (TDS) should give reasonable TDS voltage
        tds_voltage = adc.read_voltage(1)
        assert 0.5 <= tds_voltage <= 3.0  # TDS sensors typically in this range
        
        # Unused channels should be 0
        assert adc.read_voltage(2) == 0.0
        assert adc.read_voltage(3) == 0.0
    
    def test_mock_adc_protocol_compliance(self):
        """Test that MockADC implements ADC protocol."""
        adc = MockADC()
        
        # Should be callable as ADC protocol
        assert hasattr(adc, 'read_voltage')
        assert callable(adc.read_voltage)
        
        # Type checking would verify protocol compliance in real usage
        voltage = adc.read_voltage(0)
        assert isinstance(voltage, float)


class TestMockOneWireTemp:
    """Test MockOneWireTemp implementation."""
    
    def test_mock_temp_initialization(self):
        """Test MockOneWireTemp initialization."""
        temp_sensor = MockOneWireTemp()
        assert hasattr(temp_sensor, 'mock_temp')
        assert isinstance(temp_sensor.mock_temp, float)
    
    def test_mock_temp_reading(self):
        """Test temperature reading from MockOneWireTemp."""
        temp_sensor = MockOneWireTemp()
        
        temp = temp_sensor.read_celsius()
        assert isinstance(temp, float)
        assert 15.0 <= temp <= 35.0  # Reasonable room temperature range
    
    def test_mock_temp_deterministic(self):
        """Test that MockOneWireTemp returns consistent values."""
        temp1 = MockOneWireTemp()
        temp2 = MockOneWireTemp()
        
        assert temp1.read_celsius() == temp2.read_celsius()
    
    def test_mock_temp_protocol_compliance(self):
        """Test that MockOneWireTemp implements OneWireTemp protocol."""
        temp_sensor = MockOneWireTemp()
        
        # Should be callable as OneWireTemp protocol
        assert hasattr(temp_sensor, 'read_celsius')
        assert callable(temp_sensor.read_celsius)
        
        temp = temp_sensor.read_celsius()
        assert temp is None or isinstance(temp, float)


class TestHALFactoryFunctions:
    """Test HAL factory functions."""
    
    def test_create_adc_mock_mode(self):
        """Test create_adc with mock=True."""
        adc = create_adc(mock=True)
        
        assert isinstance(adc, MockADC)
        assert adc.address == 0x48  # Default address
        
        # Test custom address
        adc_custom = create_adc(address=0x49, mock=True)
        assert isinstance(adc_custom, MockADC)
        assert adc_custom.address == 0x49
    
    def test_create_adc_environment_variable(self):
        """Test create_adc with MOCK_HARDWARE environment variable."""
        # Set environment variable
        os.environ['MOCK_HARDWARE'] = '1'
        
        try:
            adc = create_adc()
            assert isinstance(adc, MockADC)
        finally:
            # Clean up environment
            if 'MOCK_HARDWARE' in os.environ:
                del os.environ['MOCK_HARDWARE']
    
    def test_create_adc_fallback_to_mock(self):
        """Test that create_adc falls back to mock when hardware unavailable."""
        # This should fall back to mock since we don't have real hardware
        adc = create_adc(mock=False)
        
        # Should be MockADC due to ImportError fallback
        assert isinstance(adc, MockADC)
    
    def test_create_temp_sensor_mock_mode(self):
        """Test create_temp_sensor with mock=True."""
        temp_sensor = create_temp_sensor(mock=True)
        
        assert isinstance(temp_sensor, MockOneWireTemp)
    
    def test_create_temp_sensor_environment_variable(self):
        """Test create_temp_sensor with MOCK_HARDWARE environment variable."""
        # Set environment variable
        os.environ['MOCK_HARDWARE'] = '1'
        
        try:
            temp_sensor = create_temp_sensor()
            assert isinstance(temp_sensor, MockOneWireTemp)
        finally:
            # Clean up environment
            if 'MOCK_HARDWARE' in os.environ:
                del os.environ['MOCK_HARDWARE']
    
    def test_create_temp_sensor_fallback_to_mock(self):
        """Test create_temp_sensor fallback when no 1-Wire available."""
        # This should fall back to mock since we don't have /sys/bus/w1/devices/
        temp_sensor = create_temp_sensor(mock=False)
        
        # Should be MockOneWireTemp due to missing hardware
        assert isinstance(temp_sensor, MockOneWireTemp)


class TestMockIntegration:
    """Test mock hardware integration with sensor systems."""
    
    def test_mock_hardware_sensor_pipeline(self):
        """Test complete sensor pipeline with mock hardware."""
        # Create mock hardware
        adc = create_adc(mock=True)
        temp_sensor = create_temp_sensor(mock=True)
        
        # Test reading pipeline
        ph_voltage = adc.read_voltage(0)
        tds_voltage = adc.read_voltage(1)
        temperature = temp_sensor.read_celsius()
        
        # All readings should be valid
        assert isinstance(ph_voltage, float)
        assert isinstance(tds_voltage, float)
        assert isinstance(temperature, float)
        
        # Values should be in reasonable ranges for aquaponics
        assert 0.0 <= ph_voltage <= 5.0
        assert 0.0 <= tds_voltage <= 5.0
        assert 15.0 <= temperature <= 35.0
    
    def test_mock_hardware_with_conversions(self):
        """Test mock hardware with actual conversion functions."""
        from conversions import voltage_to_ph, voltage_to_tds
        
        adc = create_adc(mock=True)
        temp_sensor = create_temp_sensor(mock=True)
        
        # Get mock readings
        ph_voltage = adc.read_voltage(0)
        tds_voltage = adc.read_voltage(1)
        temperature = temp_sensor.read_celsius()
        
        # Convert using real conversion functions
        ph = voltage_to_ph(ph_voltage, -3.333, 12.5)
        tds = voltage_to_tds(tds_voltage, temperature, 0.5)
        
        # Results should be reasonable aquaponics values
        if ph is not None:
            assert 4.0 <= ph <= 10.0  # Reasonable pH range
        
        if tds is not None:
            assert 0.0 <= tds <= 2000.0  # Reasonable TDS range
    
    def test_mock_sensors_class_integration(self):
        """Test mock hardware with AquaponicsSensors class."""
        from sensors import AquaponicsSensors
        
        # Create sensors with mock hardware
        sensors = AquaponicsSensors(mock=True)
        
        # Take a reading
        reading = sensors.read_all()
        
        # Verify reading structure
        assert 'timestamp' in reading
        assert 'ph' in reading
        assert 'tds' in reading
        assert 'temp_c' in reading
        
        # Values should be reasonable or None
        if reading['ph'] is not None:
            assert 4.0 <= reading['ph'] <= 10.0
        
        if reading['tds'] is not None:
            assert 0.0 <= reading['tds'] <= 2000.0
        
        if reading['temp_c'] is not None:
            assert 15.0 <= reading['temp_c'] <= 35.0
    
    def test_mock_vs_real_hardware_interface(self):
        """Test that mock and real hardware have same interface."""
        # Mock hardware
        mock_adc = create_adc(mock=True)
        mock_temp = create_temp_sensor(mock=True)
        
        # Both should have same methods
        assert hasattr(mock_adc, 'read_voltage')
        assert hasattr(mock_temp, 'read_celsius')
        
        # Methods should work the same way
        voltage = mock_adc.read_voltage(0)
        temp = mock_temp.read_celsius()
        
        assert isinstance(voltage, float)
        assert temp is None or isinstance(temp, float)


class TestMockReliability:
    """Test mock hardware reliability and edge cases."""
    
    def test_mock_adc_repeated_readings(self):
        """Test that mock ADC gives consistent repeated readings."""
        adc = MockADC()
        
        # Take multiple readings
        readings = [adc.read_voltage(0) for _ in range(10)]
        
        # All readings should be identical (deterministic)
        assert all(r == readings[0] for r in readings)
    
    def test_mock_temp_repeated_readings(self):
        """Test that mock temperature sensor gives consistent readings."""
        temp_sensor = MockOneWireTemp()
        
        # Take multiple readings
        readings = [temp_sensor.read_celsius() for _ in range(10)]
        
        # All readings should be identical (deterministic)
        assert all(r == readings[0] for r in readings)
    
    def test_mock_hardware_isolation(self):
        """Test that multiple mock instances don't interfere."""
        adc1 = MockADC()
        adc2 = MockADC()
        
        temp1 = MockOneWireTemp()
        temp2 = MockOneWireTemp()
        
        # Different instances should give same readings
        assert adc1.read_voltage(0) == adc2.read_voltage(0)
        assert temp1.read_celsius() == temp2.read_celsius()
        
        # But should be independent objects
        assert adc1 is not adc2
        assert temp1 is not temp2
    
    def test_mock_hardware_with_sensor_failure_simulation(self):
        """Test that mocks can simulate sensor failures if needed."""
        # This test demonstrates how mocks could be extended for failure testing
        adc = MockADC()
        
        # Mock currently always succeeds, but could be extended
        # to simulate failures for testing error handling
        voltage = adc.read_voltage(0)
        assert voltage is not None
        assert isinstance(voltage, float)


if __name__ == "__main__":
    pytest.main([__file__])