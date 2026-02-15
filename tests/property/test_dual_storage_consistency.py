"""Property-based tests for dual storage consistency.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone
import json
import uuid

from shared.storage.dual_storage import DualStorageClient, DualStorageError

# Feature: conversational-interface-agent, Property 20: Dual Storage Consistency
# For any system output (metadata, feedback, workflow execution, escalation),
# the data should be stored as a JSON file in S3 and as a record in the
# corresponding Glue Catalog table with matching content.


# Hypothesis strategies for generating test data
@st.composite
def metadata_strategy(draw):
    """Generate valid metadata records."""
    return {
        "brandid": draw(st.integers(min_value=1, max_value=10000)),
        "brandname": draw(st.text(min_size=1, max_size=50)),
        "regex": draw(st.text(min_size=1, max_size=100)),
        "confidence_score": draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        "version": draw(st.integers(min_value=1, max_value=100)),
    }


@st.composite
def feedback_strategy(draw):
    """Generate valid feedback records."""
    return {
        "brandid": draw(st.integers(min_value=1, max_value=10000)),
        "feedback_text": draw(st.text(min_size=1, max_size=500)),
        "category": draw(st.sampled_from(["regex_correction", "category_adjustment", "general_comment"])),
        "submitted_by": draw(st.text(min_size=1, max_size=50)),
    }


@st.composite
def workflow_execution_strategy(draw):
    """Generate valid workflow execution records."""
    return {
        "execution_arn": f"arn:aws:states:eu-west-1:123456789012:execution:workflow:{draw(st.text(min_size=10, max_size=50))}",
        "brandid": draw(st.integers(min_value=1, max_value=10000)),
        "status": draw(st.sampled_from(["RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"])),
        "start_time": draw(st.datetimes().map(lambda dt: dt.isoformat())),
    }


@st.composite
def escalation_strategy(draw):
    """Generate valid escalation records."""
    return {
        "brandid": draw(st.integers(min_value=1, max_value=10000)),
        "brandname": draw(st.text(min_size=1, max_size=50)),
        "reason": draw(st.text(min_size=1, max_size=200)),
        "confidence_score": draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
    }


@pytest.mark.property
class TestDualStorageConsistency:
    """Property 20: Dual Storage Consistency
    
    Property: For any system output (metadata, feedback, workflow execution, escalation),
    the data should be stored as a JSON file in S3 and as a record in the corresponding
    Glue Catalog table with matching content.
    
    Validates: Requirements 6.1, 6.2, 6.3, 6.4
    """

    @given(metadata=metadata_strategy())
    @settings(max_examples=100, deadline=1000)
    def test_metadata_dual_storage_consistency(self, metadata):
        """Property: Metadata is written to both S3 and Athena with matching content.
        
        For any metadata record, the data written to S3 should match the data
        that Athena can read from the external table.
        """
        with patch('shared.storage.dual_storage.S3Client') as mock_s3_class, \
             patch('shared.storage.dual_storage.AthenaClient') as mock_athena_class:
            
            # Setup mocks
            mock_s3 = MagicMock()
            mock_athena = MagicMock()
            mock_s3_class.return_value = mock_s3
            mock_athena_class.return_value = mock_athena
            
            # Create client
            client = DualStorageClient()
            
            # Execute write
            brandid = metadata["brandid"]
            result = client.write_metadata(brandid, metadata)
            
            # Property 1: Write operation succeeds
            assert result["status"] == "success"
            assert "s3_key" in result
            
            # Property 2: S3 write is called with correct data
            mock_s3.write_json.assert_called_once()
            s3_call_args = mock_s3.write_json.call_args
            s3_key = s3_call_args[0][0]
            s3_data = s3_call_args[0][1]
            
            # Property 3: S3 key follows expected pattern
            assert s3_key == f"metadata/brand_{brandid}.json"
            
            # Property 4: S3 data contains all original fields
            for key, value in metadata.items():
                assert key in s3_data, f"Field {key} missing from S3 data"
                assert s3_data[key] == value, f"Field {key} value mismatch"
            
            # Property 5: S3 data includes required fields
            assert "brandid" in s3_data
            assert s3_data["brandid"] == brandid
            assert "generated_at" in s3_data
            
            # Property 6: Athena table verification is called
            mock_athena.execute_query.assert_called_once()
            athena_query = mock_athena.execute_query.call_args[0][0]
            assert "generated_metadata" in athena_query
            
            # Property 7: Data is JSON serializable
            json_str = json.dumps(s3_data)
            assert json_str is not None
            
            # Property 8: Deserialized data matches original
            deserialized = json.loads(json_str)
            for key, value in metadata.items():
                assert deserialized[key] == value

    @given(feedback=feedback_strategy())
    @settings(max_examples=100, deadline=1000)
    def test_feedback_dual_storage_consistency(self, feedback):
        """Property: Feedback is written to both S3 and Athena with matching content.
        
        For any feedback record, the data written to S3 should match the data
        that Athena can read from the external table.
        """
        with patch('shared.storage.dual_storage.S3Client') as mock_s3_class, \
             patch('shared.storage.dual_storage.AthenaClient') as mock_athena_class:
            
            # Setup mocks
            mock_s3 = MagicMock()
            mock_athena = MagicMock()
            mock_s3_class.return_value = mock_s3
            mock_athena_class.return_value = mock_athena
            
            # Create client
            client = DualStorageClient()
            
            # Execute write
            brandid = feedback["brandid"]
            result = client.write_feedback(brandid, feedback)
            
            # Property 1: Write operation succeeds
            assert result["status"] == "success"
            assert "s3_key" in result
            assert "feedback_id" in result
            
            # Property 2: S3 write is called with correct data
            mock_s3.write_json.assert_called_once()
            s3_call_args = mock_s3.write_json.call_args
            s3_key = s3_call_args[0][0]
            s3_data = s3_call_args[0][1]
            
            # Property 3: S3 key follows expected pattern
            feedback_id = result["feedback_id"]
            assert s3_key == f"feedback/brand_{brandid}_{feedback_id}.json"
            
            # Property 4: S3 data contains all original fields
            for key, value in feedback.items():
                assert key in s3_data, f"Field {key} missing from S3 data"
                assert s3_data[key] == value, f"Field {key} value mismatch"
            
            # Property 5: S3 data includes required fields
            assert "brandid" in s3_data
            assert s3_data["brandid"] == brandid
            assert "feedback_id" in s3_data
            assert "submitted_at" in s3_data
            
            # Property 6: Athena table verification is called
            mock_athena.execute_query.assert_called_once()
            athena_query = mock_athena.execute_query.call_args[0][0]
            assert "feedback_history" in athena_query
            
            # Property 7: Data is JSON serializable
            json_str = json.dumps(s3_data)
            assert json_str is not None

    @given(execution=workflow_execution_strategy())
    @settings(max_examples=100, deadline=1000)
    def test_workflow_execution_dual_storage_consistency(self, execution):
        """Property: Workflow execution is written to both S3 and Athena with matching content.
        
        For any workflow execution record, the data written to S3 should match
        the data that Athena can read from the external table.
        """
        with patch('shared.storage.dual_storage.S3Client') as mock_s3_class, \
             patch('shared.storage.dual_storage.AthenaClient') as mock_athena_class:
            
            # Setup mocks
            mock_s3 = MagicMock()
            mock_athena = MagicMock()
            mock_s3_class.return_value = mock_s3
            mock_athena_class.return_value = mock_athena
            
            # Create client
            client = DualStorageClient()
            
            # Execute write
            result = client.write_workflow_execution(execution)
            
            # Property 1: Write operation succeeds
            assert result["status"] == "success"
            assert "s3_key" in result
            
            # Property 2: S3 write is called with correct data
            mock_s3.write_json.assert_called_once()
            s3_call_args = mock_s3.write_json.call_args
            s3_key = s3_call_args[0][0]
            s3_data = s3_call_args[0][1]
            
            # Property 3: S3 key follows expected pattern
            execution_id = execution["execution_arn"].split(":")[-1]
            assert s3_key == f"workflow-executions/{execution_id}.json"
            
            # Property 4: S3 data contains all original fields
            for key, value in execution.items():
                assert key in s3_data, f"Field {key} missing from S3 data"
                assert s3_data[key] == value, f"Field {key} value mismatch"
            
            # Property 5: S3 data includes required fields
            assert "start_time" in s3_data
            
            # Property 6: Athena table verification is called
            mock_athena.execute_query.assert_called_once()
            athena_query = mock_athena.execute_query.call_args[0][0]
            assert "workflow_executions" in athena_query
            
            # Property 7: Data is JSON serializable
            json_str = json.dumps(s3_data)
            assert json_str is not None

    @given(escalation=escalation_strategy())
    @settings(max_examples=100, deadline=1000)
    def test_escalation_dual_storage_consistency(self, escalation):
        """Property: Escalation is written to both S3 and Athena with matching content.
        
        For any escalation record, the data written to S3 should match the data
        that Athena can read from the external table.
        """
        with patch('shared.storage.dual_storage.S3Client') as mock_s3_class, \
             patch('shared.storage.dual_storage.AthenaClient') as mock_athena_class:
            
            # Setup mocks
            mock_s3 = MagicMock()
            mock_athena = MagicMock()
            mock_s3_class.return_value = mock_s3
            mock_athena_class.return_value = mock_athena
            
            # Create client
            client = DualStorageClient()
            
            # Execute write
            result = client.write_escalation(escalation)
            
            # Property 1: Write operation succeeds
            assert result["status"] == "success"
            assert "s3_key" in result
            assert "escalation_id" in result
            
            # Property 2: S3 write is called with correct data
            mock_s3.write_json.assert_called_once()
            s3_call_args = mock_s3.write_json.call_args
            s3_key = s3_call_args[0][0]
            s3_data = s3_call_args[0][1]
            
            # Property 3: S3 key follows expected pattern
            escalation_id = result["escalation_id"]
            brandid = escalation["brandid"]
            assert s3_key == f"escalations/brand_{brandid}_{escalation_id}.json"
            
            # Property 4: S3 data contains all original fields
            for key, value in escalation.items():
                assert key in s3_data, f"Field {key} missing from S3 data"
                assert s3_data[key] == value, f"Field {key} value mismatch"
            
            # Property 5: S3 data includes required fields
            assert "escalation_id" in s3_data
            assert "escalated_at" in s3_data
            assert "status" in s3_data
            
            # Property 6: Athena table verification is called
            mock_athena.execute_query.assert_called_once()
            athena_query = mock_athena.execute_query.call_args[0][0]
            assert "escalations" in athena_query
            
            # Property 7: Data is JSON serializable
            json_str = json.dumps(s3_data)
            assert json_str is not None


@pytest.mark.property
class TestDualStorageRollback:
    """Property tests for dual storage rollback behavior."""

    @given(metadata=metadata_strategy())
    @settings(max_examples=50, deadline=1000)
    def test_rollback_on_athena_failure(self, metadata):
        """Property: S3 write is rolled back if Athena verification fails.
        
        If Athena table verification fails after S3 write succeeds, the S3
        object should be deleted to maintain consistency.
        """
        with patch('shared.storage.dual_storage.S3Client') as mock_s3_class, \
             patch('shared.storage.dual_storage.AthenaClient') as mock_athena_class:
            
            # Setup mocks
            mock_s3 = MagicMock()
            mock_athena = MagicMock()
            mock_s3_class.return_value = mock_s3
            mock_athena_class.return_value = mock_athena
            
            # Simulate Athena failure
            mock_athena.execute_query.side_effect = Exception("Athena table not found")
            
            # Create client
            client = DualStorageClient()
            
            # Execute write and expect failure
            brandid = metadata["brandid"]
            with pytest.raises(DualStorageError):
                client.write_metadata(brandid, metadata)
            
            # Property 1: S3 write was attempted
            mock_s3.write_json.assert_called_once()
            
            # Property 2: S3 delete was called for rollback
            mock_s3.delete_key.assert_called_once()
            
            # Property 3: Delete was called with the same key as write
            write_key = mock_s3.write_json.call_args[0][0]
            delete_key = mock_s3.delete_key.call_args[0][0]
            assert write_key == delete_key

    @given(feedback=feedback_strategy())
    @settings(max_examples=50, deadline=1000)
    def test_no_partial_writes(self, feedback):
        """Property: No partial writes - either both succeed or both fail.
        
        The dual storage operation should be atomic: either data is written
        to both S3 and Athena (verified), or neither has the data.
        """
        with patch('shared.storage.dual_storage.S3Client') as mock_s3_class, \
             patch('shared.storage.dual_storage.AthenaClient') as mock_athena_class:
            
            # Setup mocks
            mock_s3 = MagicMock()
            mock_athena = MagicMock()
            mock_s3_class.return_value = mock_s3
            mock_athena_class.return_value = mock_athena
            
            # Simulate S3 failure
            mock_s3.write_json.side_effect = Exception("S3 write failed")
            
            # Create client
            client = DualStorageClient()
            
            # Execute write and expect failure
            brandid = feedback["brandid"]
            with pytest.raises(DualStorageError):
                client.write_feedback(brandid, feedback)
            
            # Property 1: S3 write was attempted
            mock_s3.write_json.assert_called_once()
            
            # Property 2: Athena verification was NOT called (S3 failed first)
            mock_athena.execute_query.assert_not_called()
            
            # Property 3: No rollback needed (S3 write never succeeded)
            mock_s3.delete_key.assert_not_called()

    @given(
        data_type=st.sampled_from(["metadata", "feedback", "workflow", "escalation"]),
        brandid=st.integers(min_value=1, max_value=10000),
    )
    @settings(max_examples=50, deadline=1000)
    def test_idempotent_writes(self, data_type, brandid):
        """Property: Multiple writes of the same data are idempotent.
        
        Writing the same data multiple times should result in the same final
        state (last write wins).
        """
        with patch('shared.storage.dual_storage.S3Client') as mock_s3_class, \
             patch('shared.storage.dual_storage.AthenaClient') as mock_athena_class:
            
            # Setup mocks
            mock_s3 = MagicMock()
            mock_athena = MagicMock()
            mock_s3_class.return_value = mock_s3
            mock_athena_class.return_value = mock_athena
            
            # Create client
            client = DualStorageClient()
            
            # Create test data based on type
            if data_type == "metadata":
                data = {"brandid": brandid, "brandname": "Test", "regex": "test.*"}
                result1 = client.write_metadata(brandid, data.copy())
                result2 = client.write_metadata(brandid, data.copy())
            elif data_type == "feedback":
                data = {"brandid": brandid, "feedback_text": "Test feedback"}
                result1 = client.write_feedback(brandid, data.copy())
                result2 = client.write_feedback(brandid, data.copy())
            elif data_type == "workflow":
                data = {
                    "execution_arn": f"arn:aws:states:eu-west-1:123456789012:execution:workflow:test-{brandid}",
                    "brandid": brandid,
                    "status": "RUNNING",
                }
                result1 = client.write_workflow_execution(data.copy())
                result2 = client.write_workflow_execution(data.copy())
            else:  # escalation
                data = {"brandid": brandid, "reason": "Test escalation"}
                result1 = client.write_escalation(data.copy())
                result2 = client.write_escalation(data.copy())
            
            # Property 1: Both writes succeed
            assert result1["status"] == "success"
            assert result2["status"] == "success"
            
            # Property 2: S3 write was called twice
            assert mock_s3.write_json.call_count == 2
            
            # Property 3: Athena verification was called twice
            assert mock_athena.execute_query.call_count == 2


@pytest.mark.property
class TestDualStorageDataIntegrity:
    """Property tests for data integrity in dual storage."""

    @given(
        metadata=metadata_strategy(),
        modification=st.sampled_from(["add_field", "remove_field", "change_type"]),
    )
    @settings(max_examples=50, deadline=1000)
    def test_data_integrity_preserved(self, metadata, modification):
        """Property: Data integrity is preserved through write and read cycle.
        
        Data written to dual storage should be retrievable with the same
        content and structure.
        """
        with patch('shared.storage.dual_storage.S3Client') as mock_s3_class, \
             patch('shared.storage.dual_storage.AthenaClient') as mock_athena_class:
            
            # Setup mocks
            mock_s3 = MagicMock()
            mock_athena = MagicMock()
            mock_s3_class.return_value = mock_s3
            mock_athena_class.return_value = mock_athena
            
            # Create client
            client = DualStorageClient()
            
            # Write metadata
            brandid = metadata["brandid"]
            result = client.write_metadata(brandid, metadata)
            
            # Get the data that was written to S3
            written_data = mock_s3.write_json.call_args[0][1]
            
            # Mock read to return the written data
            mock_s3.read_metadata.return_value = written_data
            
            # Read back the data
            read_data = client.read_metadata(brandid)
            
            # Property 1: Read data is not None
            assert read_data is not None
            
            # Property 2: All original fields are present
            for key, value in metadata.items():
                assert key in read_data
                assert read_data[key] == value
            
            # Property 3: Data types are preserved
            for key, value in metadata.items():
                assert type(read_data[key]) == type(value)

    @given(
        brandid=st.integers(min_value=1, max_value=10000),
        num_writes=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=30, deadline=1000)
    def test_concurrent_write_safety(self, brandid, num_writes):
        """Property: Multiple writes to different data types are independent.
        
        Writing to different data types (metadata, feedback, etc.) should not
        interfere with each other. Note: Multiple metadata writes for the same
        brand will overwrite (last write wins), which is expected behavior.
        """
        with patch('shared.storage.dual_storage.S3Client') as mock_s3_class, \
             patch('shared.storage.dual_storage.AthenaClient') as mock_athena_class:
            
            # Setup mocks
            mock_s3 = MagicMock()
            mock_athena = MagicMock()
            mock_s3_class.return_value = mock_s3
            mock_athena_class.return_value = mock_athena
            
            # Create client
            client = DualStorageClient()
            
            # Perform multiple writes with unique identifiers
            results = []
            for i in range(num_writes):
                # Use different brand IDs to ensure unique keys
                unique_brandid = brandid + i
                
                # Alternate between different data types
                if i % 4 == 0:
                    data = {"brandid": unique_brandid, "brandname": f"Test{i}"}
                    result = client.write_metadata(unique_brandid, data)
                elif i % 4 == 1:
                    data = {"brandid": unique_brandid, "feedback_text": f"Feedback{i}"}
                    result = client.write_feedback(unique_brandid, data)
                elif i % 4 == 2:
                    data = {
                        "execution_arn": f"arn:aws:states:eu-west-1:123456789012:execution:workflow:test-{i}",
                        "brandid": unique_brandid,
                        "status": "RUNNING",
                    }
                    result = client.write_workflow_execution(data)
                else:
                    data = {"brandid": unique_brandid, "reason": f"Escalation{i}"}
                    result = client.write_escalation(data)
                
                results.append(result)
            
            # Property 1: All writes succeed
            for result in results:
                assert result["status"] == "success"
            
            # Property 2: Each write has a unique S3 key (since we use unique brand IDs)
            s3_keys = [result["s3_key"] for result in results]
            assert len(s3_keys) == len(set(s3_keys)), "Duplicate S3 keys found"
            
            # Property 3: Total number of S3 writes matches number of operations
            assert mock_s3.write_json.call_count == num_writes
            
            # Property 4: Total number of Athena verifications matches number of operations
            assert mock_athena.execute_query.call_count == num_writes
