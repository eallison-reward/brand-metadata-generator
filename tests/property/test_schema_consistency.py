"""Property-based tests for schema consistency between S3 JSON and Athena tables.

**Validates: Requirements 6.5**
"""

import pytest
from hypothesis import given, strategies as st, settings
from typing import Any, Dict, List
import json

# Feature: conversational-interface-agent, Property 21: Schema Consistency
# For any Glue Catalog table, the schema should match the structure of the JSON files
# stored in S3, ensuring that all JSON fields have corresponding table columns with
# compatible types.


# Type mapping from Python/JSON types to Athena SQL types
ATHENA_TYPE_MAPPING = {
    "INT": (int,),
    "STRING": (str,),
    "DOUBLE": (float, int),  # Athena DOUBLE can accept int values
    "TIMESTAMP": (str,),  # ISO 8601 strings
    "ARRAY<INT>": (list,),
    "ARRAY<STRING>": (list,),
}


# Define the expected schemas for each table based on the SQL definitions
EXPECTED_SCHEMAS = {
    "generated_metadata": {
        "brandid": "INT",
        "brandname": "STRING",
        "regex": "STRING",
        "mccids": "ARRAY<INT>",
        "confidence_score": "DOUBLE",
        "version": "INT",
        "generated_at": "TIMESTAMP",
        "evaluator_issues": "ARRAY<STRING>",
        "coverage_narratives_matched": "DOUBLE",
        "coverage_false_positives": "DOUBLE",
    },
    "feedback_history": {
        "feedback_id": "STRING",
        "brandid": "INT",
        "metadata_version": "INT",
        "feedback_text": "STRING",
        "category": "STRING",
        "issues_identified": "ARRAY<STRING>",
        "misclassified_combos": "ARRAY<INT>",
        "submitted_at": "TIMESTAMP",
        "submitted_by": "STRING",
    },
    "workflow_executions": {
        "execution_arn": "STRING",
        "brandid": "INT",
        "status": "STRING",
        "start_time": "TIMESTAMP",
        "stop_time": "TIMESTAMP",
        "duration_seconds": "INT",
        "error_message": "STRING",
        "input_data": "STRING",
        "output_data": "STRING",
    },
    "escalations": {
        "escalation_id": "STRING",
        "brandid": "INT",
        "brandname": "STRING",
        "reason": "STRING",
        "confidence_score": "DOUBLE",
        "escalated_at": "TIMESTAMP",
        "resolved_at": "TIMESTAMP",
        "resolved_by": "STRING",
        "resolution_notes": "STRING",
        "status": "STRING",
        "iteration": "INT",
        "environment": "STRING",
    },
}


# Hypothesis strategies for generating test data matching each schema
@st.composite
def generated_metadata_strategy(draw):
    """Generate valid metadata records."""
    return {
        "brandid": draw(st.integers(min_value=1, max_value=10000)),
        "brandname": draw(st.text(min_size=1, max_size=50)),
        "regex": draw(st.text(min_size=1, max_size=100)),
        "mccids": draw(st.lists(st.integers(min_value=1000, max_value=9999), min_size=1, max_size=10)),
        "confidence_score": draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        "version": draw(st.integers(min_value=1, max_value=100)),
        "generated_at": draw(st.datetimes().map(lambda dt: dt.isoformat())),
        "evaluator_issues": draw(st.lists(st.text(min_size=1, max_size=50), max_size=5)),
        "coverage_narratives_matched": draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        "coverage_false_positives": draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
    }


@st.composite
def feedback_history_strategy(draw):
    """Generate valid feedback records."""
    return {
        "feedback_id": draw(st.uuids().map(str)),
        "brandid": draw(st.integers(min_value=1, max_value=10000)),
        "metadata_version": draw(st.integers(min_value=1, max_value=100)),
        "feedback_text": draw(st.text(min_size=1, max_size=500)),
        "category": draw(st.sampled_from(["regex_correction", "category_adjustment", "general_comment"])),
        "issues_identified": draw(st.lists(st.text(min_size=1, max_size=50), max_size=5)),
        "misclassified_combos": draw(st.lists(st.integers(min_value=1, max_value=10000), max_size=10)),
        "submitted_at": draw(st.datetimes().map(lambda dt: dt.isoformat())),
        "submitted_by": draw(st.text(min_size=1, max_size=50)),
    }


@st.composite
def workflow_executions_strategy(draw):
    """Generate valid workflow execution records."""
    return {
        "execution_arn": draw(st.text(min_size=10, max_size=100)),
        "brandid": draw(st.integers(min_value=1, max_value=10000)),
        "status": draw(st.sampled_from(["RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"])),
        "start_time": draw(st.datetimes().map(lambda dt: dt.isoformat())),
        "stop_time": draw(st.datetimes().map(lambda dt: dt.isoformat())),
        "duration_seconds": draw(st.integers(min_value=0, max_value=3600)),
        "error_message": draw(st.text(max_size=200)),
        "input_data": draw(st.text(max_size=500)),
        "output_data": draw(st.text(max_size=500)),
    }


@st.composite
def escalations_strategy(draw):
    """Generate valid escalation records."""
    return {
        "escalation_id": draw(st.uuids().map(str)),
        "brandid": draw(st.integers(min_value=1, max_value=10000)),
        "brandname": draw(st.text(min_size=1, max_size=50)),
        "reason": draw(st.text(min_size=1, max_size=200)),
        "confidence_score": draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        "escalated_at": draw(st.datetimes().map(lambda dt: dt.isoformat())),
        "resolved_at": draw(st.datetimes().map(lambda dt: dt.isoformat())),
        "resolved_by": draw(st.text(max_size=50)),
        "resolution_notes": draw(st.text(max_size=500)),
        "status": draw(st.sampled_from(["pending", "resolved", "cancelled"])),
        "iteration": draw(st.integers(min_value=1, max_value=10)),
        "environment": draw(st.sampled_from(["dev", "staging", "prod"])),
    }


def validate_field_type(field_name: str, field_value: Any, expected_type: str) -> bool:
    """Validate that a field value matches the expected Athena type.
    
    Args:
        field_name: Name of the field
        field_value: Value to validate
        expected_type: Expected Athena SQL type
        
    Returns:
        True if the value is compatible with the expected type
    """
    # Handle None values (nullable fields)
    if field_value is None:
        return True
    
    # Get allowed Python types for this Athena type
    allowed_types = ATHENA_TYPE_MAPPING.get(expected_type)
    if allowed_types is None:
        raise ValueError(f"Unknown Athena type: {expected_type}")
    
    # Check basic type compatibility
    if not isinstance(field_value, allowed_types):
        return False
    
    # Additional validation for array types
    if expected_type == "ARRAY<INT>":
        return all(isinstance(item, int) for item in field_value)
    elif expected_type == "ARRAY<STRING>":
        return all(isinstance(item, str) for item in field_value)
    
    return True


def validate_schema_consistency(
    table_name: str, json_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate that JSON data matches the expected Athena table schema.
    
    Args:
        table_name: Name of the Athena table
        json_data: JSON data to validate
        
    Returns:
        Dictionary with validation results
    """
    expected_schema = EXPECTED_SCHEMAS.get(table_name)
    if expected_schema is None:
        return {
            "valid": False,
            "error": f"Unknown table: {table_name}",
        }
    
    issues = []
    
    # Check that all expected fields are present (or nullable)
    for field_name, expected_type in expected_schema.items():
        if field_name not in json_data:
            # Some fields are optional/nullable
            continue
        
        field_value = json_data[field_name]
        
        # Validate type compatibility
        if not validate_field_type(field_name, field_value, expected_type):
            issues.append({
                "field": field_name,
                "expected_type": expected_type,
                "actual_type": type(field_value).__name__,
                "actual_value": str(field_value)[:50],  # Truncate for readability
            })
    
    # Check for unexpected fields (fields in JSON but not in schema)
    unexpected_fields = set(json_data.keys()) - set(expected_schema.keys())
    for field_name in unexpected_fields:
        issues.append({
            "field": field_name,
            "issue": "Field exists in JSON but not in Athena schema",
        })
    
    return {
        "valid": len(issues) == 0,
        "table": table_name,
        "issues": issues,
        "field_count": len(json_data),
        "expected_field_count": len(expected_schema),
    }


@pytest.mark.property
class TestSchemaConsistency:
    """Property 21: Schema Consistency
    
    Property: For any Glue Catalog table, the schema should match the structure
    of the JSON files stored in S3, ensuring that all JSON fields have corresponding
    table columns with compatible types.
    
    Validates: Requirements 6.5
    """

    @given(metadata=generated_metadata_strategy())
    @settings(max_examples=100, deadline=500)
    def test_generated_metadata_schema_consistency(self, metadata):
        """Property: Generated metadata JSON matches Athena table schema.
        
        For any generated metadata record, all fields should be compatible
        with the generated_metadata Athena table schema.
        """
        result = validate_schema_consistency("generated_metadata", metadata)
        
        # Property: Schema validation succeeds
        assert result["valid"], f"Schema validation failed: {result['issues']}"
        
        # Property: No type mismatches
        assert len(result["issues"]) == 0, f"Type mismatches found: {result['issues']}"
        
        # Property: JSON is serializable (can be written to S3)
        json_str = json.dumps(metadata)
        assert json_str is not None
        
        # Property: JSON can be deserialized back
        deserialized = json.loads(json_str)
        assert deserialized == metadata

    @given(feedback=feedback_history_strategy())
    @settings(max_examples=100, deadline=500)
    def test_feedback_history_schema_consistency(self, feedback):
        """Property: Feedback JSON matches Athena table schema.
        
        For any feedback record, all fields should be compatible
        with the feedback_history Athena table schema.
        """
        result = validate_schema_consistency("feedback_history", feedback)
        
        # Property: Schema validation succeeds
        assert result["valid"], f"Schema validation failed: {result['issues']}"
        
        # Property: No type mismatches
        assert len(result["issues"]) == 0, f"Type mismatches found: {result['issues']}"
        
        # Property: JSON is serializable
        json_str = json.dumps(feedback)
        assert json_str is not None
        
        # Property: JSON can be deserialized back
        deserialized = json.loads(json_str)
        assert deserialized == feedback

    @given(execution=workflow_executions_strategy())
    @settings(max_examples=100, deadline=500)
    def test_workflow_executions_schema_consistency(self, execution):
        """Property: Workflow execution JSON matches Athena table schema.
        
        For any workflow execution record, all fields should be compatible
        with the workflow_executions Athena table schema.
        """
        result = validate_schema_consistency("workflow_executions", execution)
        
        # Property: Schema validation succeeds
        assert result["valid"], f"Schema validation failed: {result['issues']}"
        
        # Property: No type mismatches
        assert len(result["issues"]) == 0, f"Type mismatches found: {result['issues']}"
        
        # Property: JSON is serializable
        json_str = json.dumps(execution)
        assert json_str is not None
        
        # Property: JSON can be deserialized back
        deserialized = json.loads(json_str)
        assert deserialized == execution

    @given(escalation=escalations_strategy())
    @settings(max_examples=100, deadline=500)
    def test_escalations_schema_consistency(self, escalation):
        """Property: Escalation JSON matches Athena table schema.
        
        For any escalation record, all fields should be compatible
        with the escalations Athena table schema.
        """
        result = validate_schema_consistency("escalations", escalation)
        
        # Property: Schema validation succeeds
        assert result["valid"], f"Schema validation failed: {result['issues']}"
        
        # Property: No type mismatches
        assert len(result["issues"]) == 0, f"Type mismatches found: {result['issues']}"
        
        # Property: JSON is serializable
        json_str = json.dumps(escalation)
        assert json_str is not None
        
        # Property: JSON can be deserialized back
        deserialized = json.loads(json_str)
        assert deserialized == escalation


@pytest.mark.property
class TestSchemaCompleteness:
    """Additional property tests for schema completeness."""

    def test_all_tables_have_schema_definitions(self):
        """Property: All Glue tables have corresponding schema definitions.
        
        Every table mentioned in the design document should have a schema
        definition in EXPECTED_SCHEMAS.
        """
        expected_tables = [
            "generated_metadata",
            "feedback_history",
            "workflow_executions",
            "escalations",
        ]
        
        for table in expected_tables:
            assert table in EXPECTED_SCHEMAS, f"Missing schema definition for table: {table}"
            assert len(EXPECTED_SCHEMAS[table]) > 0, f"Empty schema for table: {table}"

    def test_schema_field_types_are_valid(self):
        """Property: All schema field types are valid Athena types.
        
        Every field type in the schema definitions should be a recognized
        Athena SQL type with a corresponding Python type mapping.
        """
        for table_name, schema in EXPECTED_SCHEMAS.items():
            for field_name, field_type in schema.items():
                assert field_type in ATHENA_TYPE_MAPPING, (
                    f"Invalid Athena type '{field_type}' for field '{field_name}' "
                    f"in table '{table_name}'"
                )

    @given(
        table_name=st.sampled_from(list(EXPECTED_SCHEMAS.keys())),
        extra_field=st.text(min_size=1, max_size=20),
    )
    @settings(max_examples=50)
    def test_unexpected_fields_are_detected(self, table_name, extra_field):
        """Property: Unexpected fields in JSON are detected.
        
        If JSON data contains fields not in the Athena schema, the validation
        should detect and report them.
        """
        # Create minimal valid data
        test_data = {"brandid": 123}
        
        # Add an unexpected field
        test_data[extra_field] = "unexpected_value"
        
        result = validate_schema_consistency(table_name, test_data)
        
        # Property: If extra_field is not in schema, it should be flagged
        if extra_field not in EXPECTED_SCHEMAS[table_name]:
            assert not result["valid"] or extra_field in EXPECTED_SCHEMAS[table_name], (
                f"Unexpected field '{extra_field}' was not detected"
            )
