"""Dual storage utility for writing to both S3 and Athena.

This module provides transaction-like semantics for storing data in both S3 (as JSON)
and Athena (via external tables). If either operation fails, the successful operation
is rolled back to maintain consistency.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .athena_client import AthenaClient
from .s3_client import S3Client


class DualStorageError(Exception):
    """Exception raised when dual storage operation fails."""
    pass


class DualStorageClient:
    """Client for writing data to both S3 and Athena with rollback support."""

    def __init__(
        self,
        bucket: str = "brand-generator-rwrd-023-eu-west-1",
        database: str = "brand_metadata_generator_db",
        region: str = "eu-west-1",
    ):
        """Initialize dual storage client.
        
        Args:
            bucket: S3 bucket name
            database: Athena database name
            region: AWS region
        """
        self.s3_client = S3Client(bucket=bucket, region=region)
        self.athena_client = AthenaClient(database=database, region=region)
        self.bucket = bucket
        self.database = database

    def write_metadata(
        self, brandid: int, metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """Write brand metadata to both S3 and Athena.
        
        Args:
            brandid: Brand ID
            metadata: Metadata dictionary to store
            
        Returns:
            Dictionary with s3_key and status
            
        Raises:
            DualStorageError: If write fails
        """
        s3_key = f"metadata/brand_{brandid}.json"
        
        # Ensure metadata has required fields (always use the provided brandid)
        metadata["brandid"] = brandid
        if "generated_at" not in metadata:
            metadata["generated_at"] = datetime.now(timezone.utc).isoformat()
        
        return self._write_with_rollback(
            s3_key=s3_key,
            data=metadata,
            table_name="generated_metadata",
        )

    def write_feedback(
        self, brandid: int, feedback: Dict[str, Any]
    ) -> Dict[str, str]:
        """Write feedback to both S3 and Athena.
        
        Args:
            brandid: Brand ID
            feedback: Feedback dictionary to store
            
        Returns:
            Dictionary with s3_key, feedback_id, and status
            
        Raises:
            DualStorageError: If write fails
        """
        # Generate feedback ID if not present
        if "feedback_id" not in feedback:
            feedback["feedback_id"] = str(uuid.uuid4())
        
        feedback_id = feedback["feedback_id"]
        s3_key = f"feedback/brand_{brandid}_{feedback_id}.json"
        
        # Ensure feedback has required fields
        if "brandid" not in feedback:
            feedback["brandid"] = brandid
        if "submitted_at" not in feedback:
            feedback["submitted_at"] = datetime.now(timezone.utc).isoformat()
        
        result = self._write_with_rollback(
            s3_key=s3_key,
            data=feedback,
            table_name="feedback_history",
        )
        result["feedback_id"] = feedback_id
        return result

    def write_workflow_execution(
        self, execution_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Write workflow execution details to both S3 and Athena.
        
        Args:
            execution_data: Workflow execution dictionary to store
            
        Returns:
            Dictionary with s3_key and status
            
        Raises:
            DualStorageError: If write fails
        """
        execution_arn = execution_data.get("execution_arn", "")
        execution_id = execution_arn.split(":")[-1] if execution_arn else str(uuid.uuid4())
        s3_key = f"workflow-executions/{execution_id}.json"
        
        # Ensure execution data has required fields
        if "start_time" not in execution_data:
            execution_data["start_time"] = datetime.now(timezone.utc).isoformat()
        
        return self._write_with_rollback(
            s3_key=s3_key,
            data=execution_data,
            table_name="workflow_executions",
        )

    def write_escalation(
        self, escalation: Dict[str, Any]
    ) -> Dict[str, str]:
        """Write escalation to both S3 and Athena.
        
        Args:
            escalation: Escalation dictionary to store
            
        Returns:
            Dictionary with s3_key, escalation_id, and status
            
        Raises:
            DualStorageError: If write fails
        """
        # Generate escalation ID if not present
        if "escalation_id" not in escalation:
            escalation["escalation_id"] = str(uuid.uuid4())
        
        escalation_id = escalation["escalation_id"]
        brandid = escalation.get("brandid", "unknown")
        s3_key = f"escalations/brand_{brandid}_{escalation_id}.json"
        
        # Ensure escalation has required fields
        if "escalated_at" not in escalation:
            escalation["escalated_at"] = datetime.now(timezone.utc).isoformat()
        if "status" not in escalation:
            escalation["status"] = "pending"
        
        result = self._write_with_rollback(
            s3_key=s3_key,
            data=escalation,
            table_name="escalations",
        )
        result["escalation_id"] = escalation_id
        return result

    def _write_with_rollback(
        self,
        s3_key: str,
        data: Dict[str, Any],
        table_name: str,
    ) -> Dict[str, str]:
        """Write data to S3 and Athena with rollback on failure.
        
        This method implements transaction-like semantics:
        1. Write to S3 first
        2. Verify Athena can read the data (external table reads from S3)
        3. If verification fails, delete the S3 object
        
        Args:
            s3_key: S3 key for the data
            data: Data dictionary to store
            table_name: Athena table name
            
        Returns:
            Dictionary with s3_key and status
            
        Raises:
            DualStorageError: If write fails
        """
        s3_written = False
        
        try:
            # Step 1: Write to S3
            self.s3_client.write_json(s3_key, data)
            s3_written = True
            
            # Step 2: Verify Athena can access the data
            # Since Athena external tables read directly from S3, we just need
            # to verify the table exists and is accessible
            self._verify_athena_table(table_name)
            
            return {
                "s3_key": s3_key,
                "status": "success",
                "bucket": self.bucket,
                "table": table_name,
            }
            
        except Exception as e:
            # Rollback: Delete S3 object if it was written
            if s3_written:
                try:
                    self.s3_client.delete_key(s3_key)
                except Exception as rollback_error:
                    # Log rollback failure but raise original error
                    raise DualStorageError(
                        f"Write failed and rollback also failed. "
                        f"Original error: {str(e)}. "
                        f"Rollback error: {str(rollback_error)}. "
                        f"Manual cleanup may be required for S3 key: {s3_key}"
                    )
            
            raise DualStorageError(
                f"Failed to write to dual storage: {str(e)}"
            )

    def _verify_athena_table(self, table_name: str) -> None:
        """Verify that Athena table exists and is accessible.
        
        Args:
            table_name: Table name to verify
            
        Raises:
            Exception: If table is not accessible
        """
        # Simple verification: try to query the table with LIMIT 0
        # This checks table existence and permissions without reading data
        query = f"SELECT * FROM {table_name} LIMIT 0"
        self.athena_client.execute_query(query)

    def read_metadata(
        self, brandid: int
    ) -> Optional[Dict[str, Any]]:
        """Read brand metadata from S3.
        
        Args:
            brandid: Brand ID
            
        Returns:
            Metadata dictionary or None if not found
        """
        return self.s3_client.read_metadata(brandid, prefix="metadata")

    def read_feedback(
        self, brandid: int, feedback_id: str
    ) -> Optional[Dict[str, Any]]:
        """Read feedback from S3.
        
        Args:
            brandid: Brand ID
            feedback_id: Feedback ID
            
        Returns:
            Feedback dictionary or None if not found
        """
        s3_key = f"feedback/brand_{brandid}_{feedback_id}.json"
        return self.s3_client.read_json(s3_key)

    def read_workflow_execution(
        self, execution_id: str
    ) -> Optional[Dict[str, Any]]:
        """Read workflow execution from S3.
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Execution dictionary or None if not found
        """
        s3_key = f"workflow-executions/{execution_id}.json"
        return self.s3_client.read_json(s3_key)

    def read_escalation(
        self, brandid: int, escalation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Read escalation from S3.
        
        Args:
            brandid: Brand ID
            escalation_id: Escalation ID
            
        Returns:
            Escalation dictionary or None if not found
        """
        s3_key = f"escalations/brand_{brandid}_{escalation_id}.json"
        return self.s3_client.read_json(s3_key)
