"""
Test JSON schema validation for data.json and coach.json
"""

import pytest
import json
from pathlib import Path
import sys

try:
    import jsonschema
except ImportError:
    pytest.skip("jsonschema not available", allow_module_level=True)

# Add pi module to path  
sys.path.insert(0, str(Path(__file__).parent.parent / "pi"))


class TestDataSchema:
    """Test data.json schema validation."""
    
    def setup_method(self):
        """Load schema and test data."""
        schema_dir = Path(__file__).parent.parent / "schema"
        fixtures_dir = Path(__file__).parent / "fixtures"
        
        with open(schema_dir / "data.schema.json") as f:
            self.data_schema = json.load(f)
        
        with open(fixtures_dir / "sample_week.json") as f:
            self.sample_data = json.load(f)
    
    def test_schema_is_valid(self):
        """Test that the schema itself is valid."""
        # This will raise an exception if schema is invalid
        jsonschema.Draft202012Validator.check_schema(self.data_schema)
    
    def test_valid_data_validates(self):
        """Test that sample data validates against schema."""
        validator = jsonschema.Draft202012Validator(self.data_schema)
        
        # Should not raise any exceptions
        validator.validate(self.sample_data)
    
    def test_valid_single_reading(self):
        """Test validation of a single valid reading."""
        valid_reading = [
            {
                "timestamp": "2025-08-15T10:30:00.000Z",
                "ph": 7.0,
                "tds": 350.5,
                "temp_c": 22.3
            }
        ]
        
        validator = jsonschema.Draft202012Validator(self.data_schema)
        validator.validate(valid_reading)
    
    def test_null_values_allowed(self):
        """Test that null sensor values are allowed."""
        data_with_nulls = [
            {
                "timestamp": "2025-08-15T10:30:00.000Z",
                "ph": None,
                "tds": None,
                "temp_c": None
            }
        ]
        
        validator = jsonschema.Draft202012Validator(self.data_schema)
        validator.validate(data_with_nulls)
    
    def test_mixed_null_and_values(self):
        """Test mixed null and valid values."""
        mixed_data = [
            {
                "timestamp": "2025-08-15T10:30:00.000Z",
                "ph": 7.0,
                "tds": None,
                "temp_c": 22.3
            }
        ]
        
        validator = jsonschema.Draft202012Validator(self.data_schema)
        validator.validate(mixed_data)
    
    def test_invalid_ph_range(self):
        """Test that pH values outside 0-14 range are rejected."""
        invalid_ph_data = [
            {
                "timestamp": "2025-08-15T10:30:00.000Z",
                "ph": 15.0,  # Invalid: > 14
                "tds": 350.0,
                "temp_c": 22.0
            }
        ]
        
        validator = jsonschema.Draft202012Validator(self.data_schema)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid_ph_data)
    
    def test_invalid_negative_tds(self):
        """Test that negative TDS values are rejected."""
        invalid_tds_data = [
            {
                "timestamp": "2025-08-15T10:30:00.000Z",
                "ph": 7.0,
                "tds": -50.0,  # Invalid: negative
                "temp_c": 22.0
            }
        ]
        
        validator = jsonschema.Draft202012Validator(self.data_schema)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid_tds_data)
    
    def test_invalid_temp_range(self):
        """Test that temperature values outside -10 to 60°C are rejected."""
        invalid_temp_data = [
            {
                "timestamp": "2025-08-15T10:30:00.000Z",
                "ph": 7.0,
                "tds": 350.0,
                "temp_c": 70.0  # Invalid: > 60
            }
        ]
        
        validator = jsonschema.Draft202012Validator(self.data_schema)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid_temp_data)
    
    def test_missing_required_fields(self):
        """Test that missing required fields are rejected."""
        missing_timestamp = [
            {
                "ph": 7.0,
                "tds": 350.0,
                "temp_c": 22.0
                # Missing timestamp
            }
        ]
        
        validator = jsonschema.Draft202012Validator(self.data_schema)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(missing_timestamp)
    
    def test_additional_properties_rejected(self):
        """Test that additional properties are rejected."""
        extra_properties_data = [
            {
                "timestamp": "2025-08-15T10:30:00.000Z",
                "ph": 7.0,
                "tds": 350.0,
                "temp_c": 22.0,
                "extra_field": "not allowed"
            }
        ]
        
        validator = jsonschema.Draft202012Validator(self.data_schema)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(extra_properties_data)
    
    def test_wrong_data_type(self):
        """Test that wrong data types are rejected."""
        # Not an array
        wrong_type_data = {
            "timestamp": "2025-08-15T10:30:00.000Z",
            "ph": 7.0,
            "tds": 350.0,
            "temp_c": 22.0
        }
        
        validator = jsonschema.Draft202012Validator(self.data_schema)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(wrong_type_data)
    
    def test_string_values_rejected(self):
        """Test that string values for numeric fields are rejected."""
        string_values_data = [
            {
                "timestamp": "2025-08-15T10:30:00.000Z",
                "ph": "7.0",  # String instead of number
                "tds": 350.0,
                "temp_c": 22.0
            }
        ]
        
        validator = jsonschema.Draft202012Validator(self.data_schema)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(string_values_data)


class TestCoachSchema:
    """Test coach.json schema validation."""
    
    def setup_method(self):
        """Load schema and test data."""
        schema_dir = Path(__file__).parent.parent / "schema"
        
        with open(schema_dir / "coach.schema.json") as f:
            self.coach_schema = json.load(f)
        
        # Load actual coach.json if it exists
        coach_file = Path(__file__).parent.parent / "coach.json"
        if coach_file.exists():
            with open(coach_file) as f:
                self.sample_coach_data = json.load(f)
        else:
            self.sample_coach_data = None
    
    def test_schema_is_valid(self):
        """Test that the coach schema itself is valid."""
        jsonschema.Draft202012Validator.check_schema(self.coach_schema)
    
    def test_sample_coach_data_validates(self):
        """Test that existing coach.json validates if it exists."""
        if self.sample_coach_data:
            validator = jsonschema.Draft202012Validator(self.coach_schema)
            validator.validate(self.sample_coach_data)
    
    def test_valid_coach_response(self):
        """Test validation of a valid coach response."""
        valid_coach_data = {
            "timestamp": "2025-08-15T10:30:00.000Z",
            "status": "ok",
            "summary": "Water quality is excellent with all parameters in optimal range.",
            "insights": [
                {
                    "metric": "ph",
                    "trend": "Stable within optimal range",
                    "risk": "Low",
                    "recommendation": "Continue current maintenance routine"
                },
                {
                    "metric": "tds",
                    "recommendation": "TDS levels are appropriate for freshwater aquaponics"
                },
                {
                    "metric": "temp",
                    "trend": "Consistent temperature",
                    "recommendation": "Temperature is suitable for most fish species"
                }
            ]
        }
        
        validator = jsonschema.Draft202012Validator(self.coach_schema)
        validator.validate(valid_coach_data)
    
    def test_invalid_status_values(self):
        """Test that invalid status values are rejected."""
        invalid_status_data = {
            "status": "invalid_status",  # Must be ok/watch/alert
            "summary": "Test summary",
            "insights": []
        }
        
        validator = jsonschema.Draft202012Validator(self.coach_schema)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid_status_data)
    
    def test_invalid_metric_values(self):
        """Test that invalid metric values are rejected."""
        invalid_metric_data = {
            "status": "ok",
            "summary": "Test summary",
            "insights": [
                {
                    "metric": "invalid_metric",  # Must be ph/tds/temp
                    "recommendation": "Test recommendation"
                }
            ]
        }
        
        validator = jsonschema.Draft202012Validator(self.coach_schema)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid_metric_data)
    
    def test_missing_required_fields_coach(self):
        """Test that missing required fields in coach data are rejected."""
        # Missing status
        missing_status = {
            "summary": "Test summary",
            "insights": []
        }
        
        validator = jsonschema.Draft202012Validator(self.coach_schema)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(missing_status)
        
        # Missing recommendation in insight
        missing_recommendation = {
            "status": "ok",
            "summary": "Test summary",
            "insights": [
                {
                    "metric": "ph"
                    # Missing recommendation
                }
            ]
        }
        
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(missing_recommendation)
    
    def test_additional_properties_rejected_coach(self):
        """Test that additional properties are rejected in coach data."""
        extra_properties_data = {
            "status": "ok",
            "summary": "Test summary",
            "insights": [],
            "extra_field": "not allowed"
        }
        
        validator = jsonschema.Draft202012Validator(self.coach_schema)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(extra_properties_data)
    
    def test_minimal_valid_coach_data(self):
        """Test minimal valid coach data structure."""
        minimal_data = {
            "status": "watch",
            "summary": "Minimal test data",
            "insights": [
                {
                    "metric": "ph",
                    "recommendation": "Monitor pH levels"
                }
            ]
        }
        
        validator = jsonschema.Draft202012Validator(self.coach_schema)
        validator.validate(minimal_data)
    
    def test_empty_insights_array(self):
        """Test that empty insights array is valid."""
        empty_insights_data = {
            "status": "ok",
            "summary": "No specific insights available",
            "insights": []
        }
        
        validator = jsonschema.Draft202012Validator(self.coach_schema)
        validator.validate(empty_insights_data)
    
    def test_multiple_insights_same_metric(self):
        """Test multiple insights for the same metric."""
        multiple_insights_data = {
            "status": "alert",
            "summary": "Multiple pH concerns detected",
            "insights": [
                {
                    "metric": "ph",
                    "trend": "Declining",
                    "recommendation": "Check pH buffer system"
                },
                {
                    "metric": "ph",
                    "risk": "High",
                    "recommendation": "Add pH adjustment solution"
                }
            ]
        }
        
        validator = jsonschema.Draft202012Validator(self.coach_schema)
        validator.validate(multiple_insights_data)


class TestSchemaIntegration:
    """Test schema validation integration with actual data files."""
    
    def test_validate_fixture_files(self):
        """Test that all fixture files validate against schemas."""
        schema_dir = Path(__file__).parent.parent / "schema"
        fixtures_dir = Path(__file__).parent / "fixtures"
        
        # Load data schema
        with open(schema_dir / "data.schema.json") as f:
            data_schema = json.load(f)
        
        data_validator = jsonschema.Draft202012Validator(data_schema)
        
        # Test all fixture files
        for fixture_file in fixtures_dir.glob("*.json"):
            with open(fixture_file) as f:
                fixture_data = json.load(f)
            
            # Should validate without raising exceptions
            data_validator.validate(fixture_data)
    
    def test_validate_actual_data_file(self):
        """Test that actual data.json validates if it exists."""
        data_file = Path(__file__).parent.parent / "data.json"
        schema_file = Path(__file__).parent.parent / "schema" / "data.schema.json"
        
        if data_file.exists() and schema_file.exists():
            with open(schema_file) as f:
                schema = json.load(f)
            
            with open(data_file) as f:
                data = json.load(f)
            
            validator = jsonschema.Draft202012Validator(schema)
            validator.validate(data)
    
    def test_validate_actual_coach_file(self):
        """Test that actual coach.json validates if it exists."""
        coach_file = Path(__file__).parent.parent / "coach.json"
        schema_file = Path(__file__).parent.parent / "schema" / "coach.schema.json"
        
        if coach_file.exists() and schema_file.exists():
            with open(schema_file) as f:
                schema = json.load(f)
            
            with open(coach_file) as f:
                data = json.load(f)
            
            validator = jsonschema.Draft202012Validator(schema)
            validator.validate(data)


if __name__ == "__main__":
    pytest.main([__file__])