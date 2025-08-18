"""
Hardware Abstraction Layer for Aquaponics Sensors
==================================================

Defines protocols and implementations for ADC and temperature sensors.
Provides both real hardware interfaces and mock implementations for testing.
"""

from typing import Protocol, Optional
import os
import glob


class ADC(Protocol):
    """Protocol for Analog-to-Digital Converter interface."""
    
    def read_voltage(self, channel: int) -> float:
        """Read voltage from specified ADC channel.
        
        Args:
            channel: ADC channel number (0-3 for ADS1115)
            
        Returns:
            Voltage reading in volts (0.0-5.0V typical range)
        """
        ...


class OneWireTemp(Protocol):
    """Protocol for 1-Wire temperature sensor interface."""
    
    def read_celsius(self) -> Optional[float]:
        """Read temperature in Celsius.
        
        Returns:
            Temperature in Celsius, or None if reading failed
        """
        ...


class RealADS1115:
    """Real ADS1115 ADC implementation using Adafruit libraries."""
    
    def __init__(self, address: int = 0x48):
        """Initialize ADS1115 with specified I2C address.
        
        Args:
            address: I2C address (default 0x48)
        """
        try:
            import busio
            import board
            from adafruit_ads1x15.ads1115 import ADS1115
            from adafruit_ads1x15.analog_in import AnalogIn
            
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.adc = ADS1115(self.i2c, address=address)
            self.ADS1115 = ADS1115
            self.AnalogIn = AnalogIn
            self.address = address
            
        except ImportError as e:
            raise RuntimeError(f"Adafruit libraries not available: {e}")
    
    def read_voltage(self, channel: int) -> float:
        """Read voltage from ADS1115 channel."""
        # Map channel numbers to ADS1115 pins
        pin_map = {0: self.ADS1115.P0, 1: self.ADS1115.P1, 
                   2: self.ADS1115.P2, 3: self.ADS1115.P3}
        
        if channel not in pin_map:
            raise ValueError(f"Invalid channel {channel}, must be 0-3")
        
        analog_in = self.AnalogIn(self.adc, pin_map[channel])
        return analog_in.voltage


class RealDS18B20:
    """Real DS18B20 temperature sensor implementation."""
    
    def __init__(self):
        """Initialize DS18B20 sensor."""
        self.device_folder = '/sys/bus/w1/devices/'
    
    def read_celsius(self) -> Optional[float]:
        """Read temperature from DS18B20 via 1-Wire interface."""
        try:
            # Find DS18B20 device (starts with 28-)
            device_files = glob.glob(f"{self.device_folder}28-*")
            if not device_files:
                return None
            
            # Use first found device
            device_file = os.path.join(device_files[0], 'w1_slave')
            
            with open(device_file, 'r') as f:
                lines = f.readlines()
            
            # Check if reading is valid
            if len(lines) < 2 or lines[0].strip()[-3:] != 'YES':
                return None
            
            # Extract temperature
            temp_line = lines[1]
            equals_pos = temp_line.find('t=')
            if equals_pos == -1:
                return None
            
            temp_string = temp_line[equals_pos + 2:]
            temp_c = float(temp_string) / 1000.0
            
            return temp_c
            
        except (FileNotFoundError, ValueError, IndexError):
            return None


class MockADC:
    """Mock ADC implementation for testing."""
    
    def __init__(self, address: int = 0x48):
        """Initialize mock ADC.
        
        Args:
            address: Simulated I2C address
        """
        self.address = address
        # Deterministic mock voltages for testing
        self.mock_voltages = {
            0: 2.5,  # pH sensor - neutral pH ~ 7.0
            1: 1.8,  # TDS sensor - moderate TDS
            2: 0.0,  # Unused
            3: 0.0   # Unused
        }
    
    def read_voltage(self, channel: int) -> float:
        """Return mock voltage for specified channel."""
        if channel not in range(4):
            raise ValueError(f"Invalid channel {channel}, must be 0-3")
        
        return self.mock_voltages.get(channel, 0.0)


class MockOneWireTemp:
    """Mock DS18B20 implementation for testing."""
    
    def __init__(self):
        """Initialize mock temperature sensor."""
        self.mock_temp = 22.5  # Room temperature
    
    def read_celsius(self) -> Optional[float]:
        """Return mock temperature reading."""
        return self.mock_temp


def create_adc(address: int = 0x48, mock: bool = False) -> ADC:
    """Factory function to create ADC instance.
    
    Args:
        address: I2C address for ADS1115
        mock: If True, return mock implementation
        
    Returns:
        ADC instance (real or mock)
    """
    if mock or os.getenv('MOCK_HARDWARE', '0') == '1':
        return MockADC(address)
    
    try:
        return RealADS1115(address)
    except RuntimeError:
        # Fall back to mock if hardware unavailable
        return MockADC(address)


def create_temp_sensor(mock: bool = False) -> OneWireTemp:
    """Factory function to create temperature sensor instance.
    
    Args:
        mock: If True, return mock implementation
        
    Returns:
        OneWireTemp instance (real or mock)
    """
    if mock or os.getenv('MOCK_HARDWARE', '0') == '1':
        return MockOneWireTemp()
    
    # Check if 1-Wire is available
    if not os.path.exists('/sys/bus/w1/devices/'):
        return MockOneWireTemp()
    
    return RealDS18B20()