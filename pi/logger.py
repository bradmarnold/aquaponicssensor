"""
Data Logging and Management for Aquaponics Sensors
==================================================

Handles loading, saving, and pruning time series sensor data.
Provides atomic operations and data integrity guarantees.
"""

import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional


class DataLogger:
    """Manages sensor data persistence with automatic pruning."""
    
    def __init__(self, data_file: Path, window_days: int = 60):
        """Initialize data logger.
        
        Args:
            data_file: Path to JSON data file
            window_days: Number of days of data to retain
        """
        self.data_file = Path(data_file)
        self.window_days = window_days
        
        # Ensure parent directory exists
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
    
    def load_data(self) -> List[Dict[str, Any]]:
        """Load sensor data from file.
        
        Returns:
            List of sensor reading dictionaries, sorted by timestamp
        """
        if not self.data_file.exists():
            return []
        
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                print(f"Warning: {self.data_file} contains invalid data format")
                return []
            
            # Sort by timestamp to ensure chronological order
            data.sort(key=lambda x: x.get('timestamp', ''))
            
            return data
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading data from {self.data_file}: {e}")
            return []
    
    def save_data(self, data: List[Dict[str, Any]]) -> bool:
        """Save sensor data to file atomically.
        
        Args:
            data: List of sensor readings to save
            
        Returns:
            True if save successful, False otherwise
        """
        try:
            # Sort data by timestamp
            data.sort(key=lambda x: x.get('timestamp', ''))
            
            # Write to temporary file first for atomic operation
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.json',
                dir=self.data_file.parent
            )
            
            try:
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Atomic rename
                os.rename(temp_path, self.data_file)
                return True
                
            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
                
        except Exception as e:
            print(f"Error saving data to {self.data_file}: {e}")
            return False
    
    def append_reading(self, reading: Dict[str, Any]) -> bool:
        """Append a new sensor reading to the data file.
        
        Args:
            reading: Sensor reading dictionary with timestamp
            
        Returns:
            True if append successful, False otherwise
        """
        # Validate reading has required fields
        if not isinstance(reading, dict) or 'timestamp' not in reading:
            print("Error: Reading must be a dict with 'timestamp' field")
            return False
        
        # Load existing data
        data = self.load_data()
        
        # Append new reading
        data.append(reading)
        
        # Prune old data
        data = self.prune_data(data)
        
        # Save updated data
        return self.save_data(data)
    
    def prune_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove data older than the retention window.
        
        Args:
            data: List of sensor readings
            
        Returns:
            Pruned list with only recent data
        """
        if not data or self.window_days <= 0:
            return data
        
        # Calculate cutoff timestamp
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.window_days)
        cutoff_iso = cutoff_time.isoformat()
        
        # Filter data to keep only recent readings
        pruned_data = []
        for reading in data:
            timestamp = reading.get('timestamp', '')
            if timestamp >= cutoff_iso:
                pruned_data.append(reading)
        
        return pruned_data
    
    def get_recent_data(self, days: int) -> List[Dict[str, Any]]:
        """Get data from the last N days.
        
        Args:
            days: Number of days to retrieve
            
        Returns:
            List of readings from the specified time period
        """
        data = self.load_data()
        
        if days <= 0:
            return data
        
        # Calculate cutoff timestamp
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff_time.isoformat()
        
        # Filter data
        recent_data = []
        for reading in data:
            timestamp = reading.get('timestamp', '')
            if timestamp >= cutoff_iso:
                recent_data.append(reading)
        
        return recent_data
    
    def get_data_stats(self) -> Dict[str, Any]:
        """Get statistics about the data file.
        
        Returns:
            Dictionary with data statistics
        """
        data = self.load_data()
        
        if not data:
            return {
                "total_readings": 0,
                "file_exists": self.data_file.exists(),
                "file_size_bytes": 0,
                "oldest_reading": None,
                "newest_reading": None,
                "days_covered": 0
            }
        
        timestamps = [r.get('timestamp', '') for r in data if r.get('timestamp')]
        timestamps.sort()
        
        # Calculate days covered
        days_covered = 0
        if len(timestamps) >= 2:
            try:
                oldest = datetime.fromisoformat(timestamps[0].replace('Z', '+00:00'))
                newest = datetime.fromisoformat(timestamps[-1].replace('Z', '+00:00'))
                days_covered = (newest - oldest).days
            except ValueError:
                pass
        
        return {
            "total_readings": len(data),
            "file_exists": self.data_file.exists(),
            "file_size_bytes": self.data_file.stat().st_size if self.data_file.exists() else 0,
            "oldest_reading": timestamps[0] if timestamps else None,
            "newest_reading": timestamps[-1] if timestamps else None,
            "days_covered": days_covered
        }


def load_data_from_file(file_path: Path) -> List[Dict[str, Any]]:
    """Load sensor data from JSON file.
    
    Args:
        file_path: Path to data file
        
    Returns:
        List of sensor readings
    """
    logger = DataLogger(file_path)
    return logger.load_data()


def save_data_to_file(data: List[Dict[str, Any]], file_path: Path) -> bool:
    """Save sensor data to JSON file.
    
    Args:
        data: List of sensor readings
        file_path: Path to data file
        
    Returns:
        True if save successful, False otherwise
    """
    logger = DataLogger(file_path)
    return logger.save_data(data)


def append_reading_to_file(reading: Dict[str, Any], file_path: Path, 
                          window_days: int = 60) -> bool:
    """Append sensor reading to data file with automatic pruning.
    
    Args:
        reading: Sensor reading dictionary
        file_path: Path to data file
        window_days: Days of data to retain
        
    Returns:
        True if append successful, False otherwise
    """
    logger = DataLogger(file_path, window_days)
    return logger.append_reading(reading)


def prune_data_file(file_path: Path, window_days: int = 60) -> bool:
    """Prune old data from file, keeping only recent readings.
    
    Args:
        file_path: Path to data file
        window_days: Days of data to retain
        
    Returns:
        True if pruning successful, False otherwise
    """
    logger = DataLogger(file_path, window_days)
    data = logger.load_data()
    pruned_data = logger.prune_data(data)
    
    if len(pruned_data) != len(data):
        print(f"Pruned {len(data) - len(pruned_data)} old readings")
        return logger.save_data(pruned_data)
    
    return True  # No pruning needed


def validate_data_integrity(file_path: Path) -> Dict[str, Any]:
    """Validate data file integrity and structure.
    
    Args:
        file_path: Path to data file
        
    Returns:
        Validation results dictionary
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "total_readings": 0,
        "valid_readings": 0
    }
    
    try:
        data = load_data_from_file(file_path)
        results["total_readings"] = len(data)
        
        for i, reading in enumerate(data):
            # Check required fields
            if not isinstance(reading, dict):
                results["errors"].append(f"Reading {i}: Not a dictionary")
                continue
            
            if "timestamp" not in reading:
                results["errors"].append(f"Reading {i}: Missing timestamp")
                continue
            
            # Validate timestamp format
            try:
                datetime.fromisoformat(reading["timestamp"].replace('Z', '+00:00'))
            except ValueError:
                results["errors"].append(f"Reading {i}: Invalid timestamp format")
                continue
            
            # Check sensor fields
            for field in ["ph", "tds", "temp_c"]:
                if field not in reading:
                    results["warnings"].append(f"Reading {i}: Missing {field}")
                elif reading[field] is not None and not isinstance(reading[field], (int, float)):
                    results["errors"].append(f"Reading {i}: {field} is not numeric")
            
            results["valid_readings"] += 1
        
        # Check chronological order
        timestamps = [r.get("timestamp", "") for r in data]
        if timestamps != sorted(timestamps):
            results["warnings"].append("Readings are not in chronological order")
        
    except Exception as e:
        results["errors"].append(f"Failed to load data: {e}")
        results["valid"] = False
    
    results["valid"] = len(results["errors"]) == 0
    
    return results