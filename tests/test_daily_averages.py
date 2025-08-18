"""
Test daily averages calculation (Python port of frontend logic)
"""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
import json
import statistics

# Add pi module to path  
sys.path.insert(0, str(Path(__file__).parent.parent / "pi"))


def parse_utc_date(timestamp_str):
    """Parse UTC timestamp and return date string (YYYY-MM-DD)."""
    try:
        # Handle both Z suffix and +00:00 timezone
        if timestamp_str.endswith('Z'):
            dt = datetime.fromisoformat(timestamp_str[:-1] + '+00:00')
        else:
            dt = datetime.fromisoformat(timestamp_str)
        
        # Convert to UTC if not already
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        elif dt.tzinfo != timezone.utc:
            dt = dt.astimezone(timezone.utc)
        
        return dt.strftime('%Y-%m-%d')
    except:
        return None


def calculate_daily_averages(data, metric='ph'):
    """Calculate daily averages for a metric, matching frontend logic."""
    daily_data = {}
    
    for reading in data:
        timestamp = reading.get('timestamp', '')
        date_str = parse_utc_date(timestamp)
        
        if not date_str:
            continue
        
        # Get metric value, handling both temp_c and temp keys
        if metric == 'temp':
            value = reading.get('temp_c') or reading.get('temp')
        else:
            value = reading.get(metric)
        
        # Skip null values and zeros (treated as null in frontend)
        if value is None or value == 0:
            continue
        
        if not isinstance(value, (int, float)):
            continue
        
        if date_str not in daily_data:
            daily_data[date_str] = []
        
        daily_data[date_str].append(value)
    
    # Calculate averages
    averages = {}
    for date_str, values in daily_data.items():
        if values:
            averages[date_str] = statistics.mean(values)
    
    return averages


def filter_last_n_days(data, days=30):
    """Filter data to last N days from latest timestamp."""
    if not data:
        return []
    
    # Find latest timestamp
    latest_time = None
    for reading in data:
        timestamp = reading.get('timestamp', '')
        try:
            if timestamp.endswith('Z'):
                dt = datetime.fromisoformat(timestamp[:-1] + '+00:00')
            else:
                dt = datetime.fromisoformat(timestamp)
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            elif dt.tzinfo != timezone.utc:
                dt = dt.astimezone(timezone.utc)
            
            if latest_time is None or dt > latest_time:
                latest_time = dt
        except:
            continue
    
    if latest_time is None:
        return []
    
    # Filter to last N days
    cutoff = latest_time - timedelta(days=days)
    filtered_data = []
    
    for reading in data:
        timestamp = reading.get('timestamp', '')
        try:
            if timestamp.endswith('Z'):
                dt = datetime.fromisoformat(timestamp[:-1] + '+00:00')
            else:
                dt = datetime.fromisoformat(timestamp)
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            elif dt.tzinfo != timezone.utc:
                dt = dt.astimezone(timezone.utc)
            
            if dt >= cutoff:
                filtered_data.append(reading)
        except:
            continue
    
    return filtered_data


class TestDailyAverages:
    """Test daily average calculations."""
    
    def setup_method(self):
        """Load test fixtures."""
        fixtures_dir = Path(__file__).parent / "fixtures"
        
        with open(fixtures_dir / "sample_week.json") as f:
            self.week_data = json.load(f)
        
        with open(fixtures_dir / "sample_30d.json") as f:
            self.month_data = json.load(f)
    
    def test_parse_utc_date(self):
        """Test UTC date parsing."""
        # ISO format with Z
        assert parse_utc_date("2025-08-15T14:30:00.000Z") == "2025-08-15"
        
        # ISO format with timezone
        assert parse_utc_date("2025-08-15T14:30:00.000+00:00") == "2025-08-15"
        
        # Different timezone (should convert to UTC)
        # For simplicity, we'll assume all timestamps are already UTC
        
        # Invalid formats
        assert parse_utc_date("invalid") is None
        assert parse_utc_date("") is None
    
    def test_calculate_daily_averages_ph(self):
        """Test pH daily averages calculation."""
        averages = calculate_daily_averages(self.week_data, 'ph')
        
        # Should have multiple days
        assert len(averages) > 1
        
        # All values should be reasonable pH values
        for date_str, avg_ph in averages.items():
            assert isinstance(avg_ph, float)
            assert 6.0 <= avg_ph <= 8.0  # Reasonable pH range
            assert len(date_str) == 10  # YYYY-MM-DD format
    
    def test_calculate_daily_averages_tds(self):
        """Test TDS daily averages calculation."""
        averages = calculate_daily_averages(self.week_data, 'tds')
        
        # Should have multiple days
        assert len(averages) > 1
        
        # All values should be reasonable TDS values
        for date_str, avg_tds in averages.items():
            assert isinstance(avg_tds, float)
            assert 200 <= avg_tds <= 600  # Reasonable TDS range for aquaponics
    
    def test_calculate_daily_averages_temp(self):
        """Test temperature daily averages calculation."""
        averages = calculate_daily_averages(self.week_data, 'temp')
        
        # Should have multiple days
        assert len(averages) > 1
        
        # All values should be reasonable temperature values
        for date_str, avg_temp in averages.items():
            assert isinstance(avg_temp, float)
            assert 15.0 <= avg_temp <= 35.0  # Reasonable temperature range
    
    def test_calculate_daily_averages_with_nulls(self):
        """Test daily averages with null and zero values."""
        test_data = [
            {"timestamp": "2025-08-15T10:00:00.000Z", "ph": 7.0, "tds": 350.0, "temp_c": 22.0},
            {"timestamp": "2025-08-15T10:30:00.000Z", "ph": None, "tds": 0, "temp_c": 23.0},
            {"timestamp": "2025-08-15T11:00:00.000Z", "ph": 6.8, "tds": 340.0, "temp_c": None},
            {"timestamp": "2025-08-16T10:00:00.000Z", "ph": 7.2, "tds": 360.0, "temp_c": 24.0}
        ]
        
        ph_averages = calculate_daily_averages(test_data, 'ph')
        tds_averages = calculate_daily_averages(test_data, 'tds')
        temp_averages = calculate_daily_averages(test_data, 'temp')
        
        # Should only count non-null, non-zero values
        assert "2025-08-15" in ph_averages
        assert ph_averages["2025-08-15"] == pytest.approx((7.0 + 6.8) / 2)
        
        assert "2025-08-15" in tds_averages
        assert tds_averages["2025-08-15"] == pytest.approx((350.0 + 340.0) / 2)
        
        assert "2025-08-15" in temp_averages
        assert temp_averages["2025-08-15"] == pytest.approx((22.0 + 23.0) / 2)
    
    def test_calculate_daily_averages_empty_data(self):
        """Test daily averages with empty data."""
        averages = calculate_daily_averages([], 'ph')
        assert averages == {}
        
        # Data with no valid readings
        invalid_data = [
            {"timestamp": "invalid", "ph": 7.0},
            {"timestamp": "2025-08-15T10:00:00.000Z", "ph": None},
            {"timestamp": "2025-08-15T10:30:00.000Z", "ph": 0}
        ]
        
        averages = calculate_daily_averages(invalid_data, 'ph')
        assert averages == {}
    
    def test_filter_last_n_days(self):
        """Test filtering data to last N days."""
        # Filter to last 3 days (should reduce the dataset)
        filtered_data = filter_last_n_days(self.month_data, 3)
        
        assert len(filtered_data) < len(self.month_data)
        assert len(filtered_data) > 0
        
        # All filtered data should be within 3 days of latest
        if filtered_data:
            timestamps = []
            for reading in filtered_data:
                timestamp = reading.get('timestamp', '')
                try:
                    if timestamp.endswith('Z'):
                        dt = datetime.fromisoformat(timestamp[:-1] + '+00:00')
                    else:
                        dt = datetime.fromisoformat(timestamp)
                    timestamps.append(dt)
                except:
                    continue
            
            if timestamps:
                latest = max(timestamps)
                earliest = min(timestamps)
                time_span = latest - earliest
                assert time_span.days <= 3
    
    def test_filter_last_n_days_edge_cases(self):
        """Test edge cases for date filtering."""
        # Empty data
        assert filter_last_n_days([], 7) == []
        
        # Invalid timestamps
        invalid_data = [{"timestamp": "invalid", "ph": 7.0}]
        assert filter_last_n_days(invalid_data, 7) == []
        
        # Single day of data
        single_day = [{"timestamp": "2025-08-15T10:00:00.000Z", "ph": 7.0}]
        filtered = filter_last_n_days(single_day, 7)
        assert len(filtered) == 1
    
    def test_daily_averages_integration(self):
        """Test full integration: filter + calculate averages."""
        # Get last 7 days and calculate daily averages
        recent_data = filter_last_n_days(self.month_data, 7)
        ph_averages = calculate_daily_averages(recent_data, 'ph')
        
        # Should have some daily averages
        assert len(ph_averages) > 0
        
        # All dates should be within last 7 days
        latest_date = max(ph_averages.keys())
        earliest_date = min(ph_averages.keys())
        
        latest_dt = datetime.strptime(latest_date, '%Y-%m-%d')
        earliest_dt = datetime.strptime(earliest_date, '%Y-%m-%d')
        
        assert (latest_dt - earliest_dt).days <= 7
    
    def test_frontend_compatibility(self):
        """Test that calculations match frontend expectations."""
        # Test with known data
        test_data = [
            {"timestamp": "2025-08-15T10:00:00.000Z", "ph": 7.0, "tds": 350.0, "temp_c": 22.0},
            {"timestamp": "2025-08-15T14:00:00.000Z", "ph": 6.8, "tds": 360.0, "temp_c": 23.0},
            {"timestamp": "2025-08-16T10:00:00.000Z", "ph": 7.2, "tds": 340.0, "temp_c": 21.5},
        ]
        
        ph_averages = calculate_daily_averages(test_data, 'ph')
        
        # Should group by UTC date
        assert "2025-08-15" in ph_averages
        assert "2025-08-16" in ph_averages
        
        # Aug 15 should average 7.0 and 6.8
        assert ph_averages["2025-08-15"] == pytest.approx(6.9)
        
        # Aug 16 should just be 7.2
        assert ph_averages["2025-08-16"] == pytest.approx(7.2)


class TestTemperatureHandling:
    """Test handling of both temp_c and temp fields."""
    
    def test_temp_c_field(self):
        """Test with temp_c field (preferred)."""
        data = [{"timestamp": "2025-08-15T10:00:00.000Z", "temp_c": 22.5}]
        averages = calculate_daily_averages(data, 'temp')
        assert "2025-08-15" in averages
        assert averages["2025-08-15"] == 22.5
    
    def test_temp_field_fallback(self):
        """Test fallback to temp field."""
        data = [{"timestamp": "2025-08-15T10:00:00.000Z", "temp": 23.0}]
        averages = calculate_daily_averages(data, 'temp')
        assert "2025-08-15" in averages
        assert averages["2025-08-15"] == 23.0
    
    def test_temp_c_preferred_over_temp(self):
        """Test that temp_c is preferred when both exist."""
        data = [{"timestamp": "2025-08-15T10:00:00.000Z", "temp_c": 22.5, "temp": 99.9}]
        averages = calculate_daily_averages(data, 'temp')
        assert "2025-08-15" in averages
        assert averages["2025-08-15"] == 22.5  # Should use temp_c, not temp


if __name__ == "__main__":
    pytest.main([__file__])