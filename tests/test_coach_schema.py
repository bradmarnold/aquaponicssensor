"""
Test coach.json schema validation specifically
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


class TestCoachSchemaValidation:
    """Test coach.json schema validation in detail."""
    
    def setup_method(self):
        """Load coach schema."""
        schema_dir = Path(__file__).parent.parent / "schema"
        
        with open(schema_dir / "coach.schema.json") as f:
            self.coach_schema = json.load(f)
        
        self.validator = jsonschema.Draft202012Validator(self.coach_schema)
    
    def test_openai_structured_output_format(self):
        """Test that schema matches OpenAI Structured Output requirements."""
        # The schema should be compatible with OpenAI's structured outputs
        # This means it should be a valid JSON Schema with proper constraints
        
        # Check basic structure
        assert self.coach_schema["type"] == "object"
        assert "properties" in self.coach_schema
        assert "required" in self.coach_schema
        
        # Check required fields match what's in pi/coach.py
        required_fields = self.coach_schema["required"]
        assert "status" in required_fields
        assert "summary" in required_fields
        assert "insights" in required_fields
    
    def test_status_enum_values(self):
        """Test that status enum has correct values."""
        status_prop = self.coach_schema["properties"]["status"]
        assert status_prop["type"] == "string"
        assert status_prop["enum"] == ["ok", "watch", "alert"]
    
    def test_insights_array_structure(self):
        """Test insights array structure."""
        insights_prop = self.coach_schema["properties"]["insights"]
        assert insights_prop["type"] == "array"
        
        # Check insight item structure
        insight_item = insights_prop["items"]
        assert insight_item["type"] == "object"
        
        # Check metric enum
        metric_prop = insight_item["properties"]["metric"]
        assert metric_prop["enum"] == ["ph", "tds", "temp"]
        
        # Check required fields for insights
        assert "metric" in insight_item["required"]
        assert "recommendation" in insight_item["required"]
    
    def test_complete_coach_response(self):
        """Test a complete coach response structure."""
        complete_response = {
            "timestamp": "2025-08-15T10:30:00.000Z",
            "status": "watch",
            "summary": "pH levels are slightly below optimal range. TDS and temperature are within acceptable limits.",
            "insights": [
                {
                    "metric": "ph",
                    "trend": "Slightly declining over past 24 hours",
                    "risk": "Moderate - below optimal range",
                    "recommendation": "Check pH probe calibration and consider adding pH buffer to raise levels to 6.6-7.2 range"
                },
                {
                    "metric": "tds",
                    "trend": "Stable within normal range",
                    "risk": "Low - appropriate for freshwater aquaponics",
                    "recommendation": "Continue current nutrient management routine"
                },
                {
                    "metric": "temp",
                    "trend": "Consistent temperature readings",
                    "risk": "Low - suitable for most fish species",
                    "recommendation": "Monitor for seasonal variations and adjust as needed"
                }
            ]
        }
        
        # Should validate successfully
        self.validator.validate(complete_response)
    
    def test_minimal_required_fields_only(self):
        """Test response with only required fields."""
        minimal_response = {
            "status": "ok",
            "summary": "All systems normal",
            "insights": [
                {
                    "metric": "ph",
                    "recommendation": "Continue monitoring"
                }
            ]
        }
        
        self.validator.validate(minimal_response)
    
    def test_all_status_values(self):
        """Test all valid status values."""
        for status in ["ok", "watch", "alert"]:
            response = {
                "status": status,
                "summary": f"System status: {status}",
                "insights": []
            }
            self.validator.validate(response)
    
    def test_all_metric_values(self):
        """Test all valid metric values."""
        for metric in ["ph", "tds", "temp"]:
            response = {
                "status": "ok",
                "summary": f"Testing {metric} metric",
                "insights": [
                    {
                        "metric": metric,
                        "recommendation": f"Monitor {metric} levels"
                    }
                ]
            }
            self.validator.validate(response)
    
    def test_optional_insight_fields(self):
        """Test that trend and risk fields are optional in insights."""
        # With trend but no risk
        response_with_trend = {
            "status": "ok",
            "summary": "Testing optional fields",
            "insights": [
                {
                    "metric": "ph",
                    "trend": "Stable",
                    "recommendation": "Continue monitoring"
                }
            ]
        }
        self.validator.validate(response_with_trend)
        
        # With risk but no trend
        response_with_risk = {
            "status": "ok", 
            "summary": "Testing optional fields",
            "insights": [
                {
                    "metric": "tds",
                    "risk": "Low",
                    "recommendation": "Continue monitoring"
                }
            ]
        }
        self.validator.validate(response_with_risk)
        
        # With both
        response_with_both = {
            "status": "ok",
            "summary": "Testing optional fields", 
            "insights": [
                {
                    "metric": "temp",
                    "trend": "Increasing",
                    "risk": "Medium",
                    "recommendation": "Monitor temperature rise"
                }
            ]
        }
        self.validator.validate(response_with_both)
    
    def test_timestamp_field_optional(self):
        """Test that timestamp field is optional in schema."""
        # Response without timestamp should still be valid
        response_no_timestamp = {
            "status": "ok",
            "summary": "No timestamp provided",
            "insights": []
        }
        self.validator.validate(response_no_timestamp)
        
        # Response with timestamp should also be valid
        response_with_timestamp = {
            "timestamp": "2025-08-15T10:30:00.000Z",
            "status": "ok", 
            "summary": "Timestamp provided",
            "insights": []
        }
        self.validator.validate(response_with_timestamp)
    
    def test_empty_insights_array(self):
        """Test that empty insights array is allowed."""
        response = {
            "status": "ok",
            "summary": "No specific insights needed",
            "insights": []
        }
        self.validator.validate(response)
    
    def test_multiple_insights_per_metric(self):
        """Test multiple insights for the same metric."""
        response = {
            "status": "alert",
            "summary": "Multiple pH issues detected",
            "insights": [
                {
                    "metric": "ph",
                    "trend": "Rapidly declining",
                    "recommendation": "Immediate pH adjustment needed"
                },
                {
                    "metric": "ph",
                    "risk": "Critical - fish health at risk",
                    "recommendation": "Emergency pH buffer addition required"
                }
            ]
        }
        self.validator.validate(response)
    
    def test_realistic_coaching_scenarios(self):
        """Test realistic coaching scenarios."""
        # Scenario 1: All good
        all_good = {
            "status": "ok",
            "summary": "Excellent water quality across all parameters",
            "insights": [
                {
                    "metric": "ph",
                    "trend": "Stable at 6.9",
                    "risk": "Low",
                    "recommendation": "Maintain current pH management routine"
                },
                {
                    "metric": "tds",
                    "trend": "Consistent around 350 ppm",
                    "risk": "Low", 
                    "recommendation": "TDS levels optimal for plant and fish health"
                },
                {
                    "metric": "temp",
                    "trend": "Stable at 22°C",
                    "risk": "Low",
                    "recommendation": "Temperature perfect for most aquaponics setups"
                }
            ]
        }
        self.validator.validate(all_good)
        
        # Scenario 2: Warning condition
        warning_condition = {
            "status": "watch",
            "summary": "TDS levels elevated, requires attention",
            "insights": [
                {
                    "metric": "tds",
                    "trend": "Increasing over past week",
                    "risk": "Moderate - approaching upper limit",
                    "recommendation": "Reduce feeding rate and increase water changes to lower TDS"
                }
            ]
        }
        self.validator.validate(warning_condition)
        
        # Scenario 3: Alert condition
        alert_condition = {
            "status": "alert",
            "summary": "Critical pH drop detected - immediate action required",
            "insights": [
                {
                    "metric": "ph",
                    "trend": "Dropped to 5.8 - dangerously low",
                    "risk": "Critical - fish stress and potential death",
                    "recommendation": "EMERGENCY: Add pH buffer immediately and check system for acid buildup"
                }
            ]
        }
        self.validator.validate(alert_condition)


if __name__ == "__main__":
    pytest.main([__file__])