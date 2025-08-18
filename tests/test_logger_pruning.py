"""
Test logger.py - Data logging and pruning functionality
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

# Add pi module to path  
sys.path.insert(0, str(Path(__file__).parent.parent / "pi"))

from logger import (
    DataLogger,
    load_data_from_file,
    save_data_to_file,
    append_reading_to_file,
    prune_data_file,
    validate_data_integrity
)


class TestDataLogger:
    """Test DataLogger class functionality."""
    
    def setup_method(self):
        """Set up test with temporary file."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = Path(self.temp_dir) / "test_data.json"
        self.logger = DataLogger(self.data_file, window_days=7)
    
    def teardown_method(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_data(self, days_back=10, interval_hours=0.5):
        """Create test data spanning multiple days."""
        data = []
        now = datetime.now(timezone.utc)
        
        for i in range(int(days_back * 24 / interval_hours)):
            timestamp = now - timedelta(hours=i * interval_hours)
            reading = {
                "timestamp": timestamp.isoformat(),
                "ph": 6.8 + (i % 10) * 0.1,  # Varying pH
                "tds": 300 + (i % 50) * 2,    # Varying TDS
                "temp_c": 22.0 + (i % 20) * 0.2  # Varying temp
            }
            data.append(reading)
        
        return data
    
    def test_load_empty_file(self):
        """Test loading from non-existent file."""
        data = self.logger.load_data()
        assert data == []
    
    def test_save_and_load_data(self):
        """Test saving and loading data."""
        test_data = self.create_test_data(days_back=2)
        
        success = self.logger.save_data(test_data)
        assert success is True
        assert self.data_file.exists()
        
        loaded_data = self.logger.load_data()
        assert len(loaded_data) == len(test_data)
        assert loaded_data[0]["timestamp"] <= loaded_data[-1]["timestamp"]  # Should be sorted
    
    def test_append_reading(self):
        """Test appending individual readings."""
        # Start with empty file
        reading1 = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ph": 7.0,
            "tds": 350.0,
            "temp_c": 23.0
        }
        
        success = self.logger.append_reading(reading1)
        assert success is True
        
        data = self.logger.load_data()
        assert len(data) == 1
        assert data[0]["ph"] == 7.0
        
        # Append another reading
        reading2 = {
            "timestamp": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
            "ph": 6.9,
            "tds": 355.0,
            "temp_c": 23.2
        }
        
        success = self.logger.append_reading(reading2)
        assert success is True
        
        data = self.logger.load_data()
        assert len(data) == 2
    
    def test_append_invalid_reading(self):
        """Test appending invalid readings."""
        # Missing timestamp
        invalid_reading = {"ph": 7.0, "tds": 350.0}
        success = self.logger.append_reading(invalid_reading)
        assert success is False
        
        # Not a dict
        success = self.logger.append_reading("invalid")
        assert success is False
    
    def test_prune_data(self):
        """Test data pruning functionality."""
        # Create data spanning 15 days
        test_data = self.create_test_data(days_back=15)
        self.logger.save_data(test_data)
        
        # Load and prune (window is 7 days)
        data = self.logger.load_data()
        pruned_data = self.logger.prune_data(data)
        
        # Should have fewer entries
        assert len(pruned_data) < len(data)
        
        # All remaining entries should be within window
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        for entry in pruned_data:
            entry_time = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
            assert entry_time >= cutoff
    
    def test_prune_data_edge_cases(self):
        """Test pruning edge cases."""
        # Empty data
        assert self.logger.prune_data([]) == []
        
        # Window = 0 (no retention)
        logger_no_retention = DataLogger(self.data_file, window_days=0)
        test_data = self.create_test_data(days_back=2)
        pruned = logger_no_retention.prune_data(test_data)
        assert pruned == test_data  # No pruning when window_days <= 0
    
    def test_get_recent_data(self):
        """Test getting recent data within time window."""
        test_data = self.create_test_data(days_back=10)
        self.logger.save_data(test_data)
        
        # Get last 3 days
        recent_data = self.logger.get_recent_data(3)
        
        # Should have some data but not all
        assert 0 < len(recent_data) < len(test_data)
        
        # All entries should be within 3 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=3)
        for entry in recent_data:
            entry_time = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
            assert entry_time >= cutoff
    
    def test_get_data_stats(self):
        """Test data statistics functionality."""
        # Empty file stats
        stats = self.logger.get_data_stats()
        assert stats["total_readings"] == 0
        assert stats["file_exists"] is False
        assert stats["oldest_reading"] is None
        
        # With data
        test_data = self.create_test_data(days_back=5)
        self.logger.save_data(test_data)
        
        stats = self.logger.get_data_stats()
        assert stats["total_readings"] == len(test_data)
        assert stats["file_exists"] is True
        assert stats["oldest_reading"] is not None
        assert stats["newest_reading"] is not None
        assert stats["days_covered"] > 0
    
    def test_atomic_save(self):
        """Test that saves are atomic (don't corrupt existing data)."""
        # Save initial data
        test_data = self.create_test_data(days_back=2)
        self.logger.save_data(test_data)
        
        # Verify file exists and is readable
        assert self.data_file.exists()
        original_data = self.logger.load_data()
        assert len(original_data) == len(test_data)
        
        # Test that file is valid JSON
        with open(self.data_file, 'r') as f:
            json.load(f)  # Should not raise exception


class TestUtilityFunctions:
    """Test utility functions for data management."""
    
    def setup_method(self):
        """Set up test with temporary file."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = Path(self.temp_dir) / "test_data.json"
    
    def teardown_method(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_reading(self, hours_ago=0):
        """Create a test reading N hours ago."""
        timestamp = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        return {
            "timestamp": timestamp.isoformat(),
            "ph": 7.0,
            "tds": 350.0,
            "temp_c": 22.5
        }
    
    def test_load_save_functions(self):
        """Test standalone load/save functions."""
        test_data = [self.create_test_reading(i) for i in range(5)]
        
        # Save data
        success = save_data_to_file(test_data, self.data_file)
        assert success is True
        
        # Load data
        loaded_data = load_data_from_file(self.data_file)
        assert len(loaded_data) == len(test_data)
    
    def test_append_reading_function(self):
        """Test standalone append reading function."""
        reading = self.create_test_reading()
        
        success = append_reading_to_file(reading, self.data_file, window_days=30)
        assert success is True
        
        data = load_data_from_file(self.data_file)
        assert len(data) == 1
        assert data[0]["ph"] == 7.0
    
    def test_prune_data_function(self):
        """Test standalone prune data function."""
        # Create data with some old entries
        old_data = [self.create_test_reading(hours_ago=24*40)]  # 40 days old
        recent_data = [self.create_test_reading(hours_ago=i) for i in range(24)]  # Last day
        all_data = old_data + recent_data
        
        save_data_to_file(all_data, self.data_file)
        
        # Prune to keep only last 30 days
        success = prune_data_file(self.data_file, window_days=30)
        assert success is True
        
        # Old data should be removed
        final_data = load_data_from_file(self.data_file)
        assert len(final_data) < len(all_data)
        
        # Should only have recent data
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        for entry in final_data:
            entry_time = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
            assert entry_time >= cutoff
    
    def test_validate_data_integrity(self):
        """Test data integrity validation."""
        # Valid data
        valid_data = [self.create_test_reading(i) for i in range(3)]
        save_data_to_file(valid_data, self.data_file)
        
        results = validate_data_integrity(self.data_file)
        assert results["valid"] is True
        assert results["total_readings"] == 3
        assert results["valid_readings"] == 3
        assert len(results["errors"]) == 0
        
        # Invalid data
        invalid_data = [
            {"timestamp": "invalid-timestamp", "ph": 7.0, "tds": 350.0, "temp_c": 22.0},
            {"ph": 7.0, "tds": 350.0, "temp_c": 22.0},  # Missing timestamp
            {"timestamp": datetime.now(timezone.utc).isoformat(), "ph": "invalid", "tds": 350.0, "temp_c": 22.0}
        ]
        save_data_to_file(invalid_data, self.data_file)
        
        results = validate_data_integrity(self.data_file)
        assert results["valid"] is False
        assert len(results["errors"]) > 0


class TestDataIntegrity:
    """Test data integrity and error handling."""
    
    def setup_method(self):
        """Set up test with temporary file."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = Path(self.temp_dir) / "test_data.json"
        self.logger = DataLogger(self.data_file, window_days=7)
    
    def teardown_method(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_corrupted_json_file(self):
        """Test handling of corrupted JSON files."""
        # Create corrupted JSON file
        with open(self.data_file, 'w') as f:
            f.write('{"invalid": json content')
        
        # Should return empty list, not crash
        data = self.logger.load_data()
        assert data == []
    
    def test_non_list_json_file(self):
        """Test handling of JSON file with wrong format."""
        # Create JSON file with object instead of array
        with open(self.data_file, 'w') as f:
            json.dump({"not": "a list"}, f)
        
        # Should return empty list
        data = self.logger.load_data()
        assert data == []
    
    def test_chronological_sorting(self):
        """Test that data is kept in chronological order."""
        # Create data out of order
        now = datetime.now(timezone.utc)
        out_of_order_data = [
            {"timestamp": (now - timedelta(hours=1)).isoformat(), "ph": 7.0, "tds": 350.0, "temp_c": 22.0},
            {"timestamp": (now - timedelta(hours=3)).isoformat(), "ph": 6.9, "tds": 345.0, "temp_c": 21.8},
            {"timestamp": (now - timedelta(hours=2)).isoformat(), "ph": 7.1, "tds": 355.0, "temp_c": 22.2}
        ]
        
        self.logger.save_data(out_of_order_data)
        loaded_data = self.logger.load_data()
        
        # Should be sorted by timestamp
        timestamps = [entry["timestamp"] for entry in loaded_data]
        assert timestamps == sorted(timestamps)


if __name__ == "__main__":
    pytest.main([__file__])