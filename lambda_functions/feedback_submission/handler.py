"""Lambda handler for feedback submission.

This tool handles feedback submission from users through the conversational interface.
It validates feedback parameters, uses feedback_processing agent tools to parse feedback,
stores feedback to S3 and the feedback_history Athena table using dual storage, and implements retry logic.

Requirements: 7.4, 3.1, 3.2, 3.3, 3.4, 3.5, 6.2
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict

from agents.feedback_processing.tools import parse_feedback
from shared.storage.athena_client import AthenaClient
from shared.storage.dual_storage import DualStorageClient
from shared.utils.base_handler import RetryableToolHandler
from shared.utils.error_handler import BackendServiceError, UserInputError


class FeedbackSubmissionHandler(RetryableToolHandler):
    """Handler for submit_feedback tool with retry logic."""
    
    def __init__(self):
        """Initialize handler with max_retries=1 as per requirements."""
        super().__init__("submit_feedback", max_retries=1, initial_delay=2.0)
        
        # Initialize dual storage client
        self.dual_storage = DualStorageClient(
            bucket="brand-generator-rwrd-023-eu-west-1",
            database="brand_metadata_generator_db",
            region="eu-west-1",
        )
        
        # Initialize Athena client for queries
        self.athena_client = AthenaClient(
            database="brand_metadata_generator_db",
            region="eu-west-1",
            output_location="s3://brand-generator-rwrd-023-eu-west-1/query-results/",
        )
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate input parameters.
        
        Args:
            parameters: Input parameters
            
        Raises:
            UserInputError: If parameters are invalid
        """
        # Validate brandid is present
        if "brandid" not in parameters:
            raise UserInputError(
                "Parameter 'brandid' is required",
                suggestion="Provide the brand ID for which feedback is being submitted",
            )
        
        brandid = parameters["brandid"]
        
        # Validate brandid type
        if not isinstance(brandid, int):
            raise UserInputError(
                f"Parameter 'brandid' must be an integer, got {type(brandid).__name__}",
                suggestion="Provide a valid integer brand ID",
            )
        
        if brandid <= 0:
            raise UserInputError(
                f"Brand ID must be positive, got {brandid}",
                suggestion="Provide a valid positive brand ID",
            )
        
        # Validate feedback_text is present
        if "feedback_text" not in parameters:
            raise UserInputError(
                "Parameter 'feedback_text' is required",
                suggestion="Provide the feedback text describing the issue",
            )
        
        feedback_text = parameters["feedback_text"]
        
        # Validate feedback_text type
        if not isinstance(feedback_text, str):
            raise UserInputError(
                f"Parameter 'feedback_text' must be a string, got {type(feedback_text).__name__}",
                suggestion="Provide feedback as a text string",
            )
        
        if not feedback_text.strip():
            raise UserInputError(
                "Parameter 'feedback_text' cannot be empty",
                suggestion="Provide meaningful feedback text describing the issue",
            )
        
        # Validate metadata_version if provided
        if "metadata_version" in parameters:
            metadata_version = parameters["metadata_version"]
            if not isinstance(metadata_version, int):
                raise UserInputError(
                    f"Parameter 'metadata_version' must be an integer, got {type(metadata_version).__name__}",
                    suggestion="Provide a valid integer metadata version or omit to use latest",
                )
            if metadata_version < 1:
                raise UserInputError(
                    f"Metadata version must be at least 1, got {metadata_version}",
                    suggestion="Provide a valid metadata version number",
                )
    
    def get_latest_metadata_version(self, brandid: int) -> int:
        """Get the latest metadata version for a brand.
        
        Args:
            brandid: Brand ID
            
        Returns:
            Latest metadata version number (defaults to 1 if not found)
        """
        try:
            # Query generated_metadata table for latest version
            results = self.athena_client.execute_query(
                f"""
                SELECT MAX(version) as max_version
                FROM generated_metadata
                WHERE brandid = {brandid}
                """
            )
            
            if results and results[0].get("max_version"):
                return results[0]["max_version"]
            else:
                # Default to version 1 if no metadata found
                self.logger.info(f"No metadata found for brand {brandid}, defaulting to version 1")
                return 1
                
        except Exception as e:
            self.logger.warning(f"Failed to get latest metadata version for brand {brandid}: {str(e)}")
            # Default to version 1 on error
            return 1
    
    def store_feedback(
        self, feedback_record: Dict[str, Any], brandid: int
    ) -> str:
        """Store feedback to both S3 and Athena using dual storage.
        
        Args:
            feedback_record: Parsed feedback record
            brandid: Brand ID
            
        Returns:
            S3 key where feedback was stored
            
        Raises:
            BackendServiceError: If dual storage write fails
        """
        try:
            result = self.dual_storage.write_feedback(brandid, feedback_record)
            self.logger.info(
                f"Feedback stored via dual storage: {result['s3_key']} "
                f"(feedback_id: {result['feedback_id']})"
            )
            return result["s3_key"]
            
        except Exception as e:
            raise BackendServiceError(
                f"Failed to store feedback via dual storage: {str(e)}",
                details=f"Brand ID: {brandid}, Feedback ID: {feedback_record.get('feedback_id')}",
                suggestion="Check S3 and Athena permissions and service status",
            )
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute feedback submission.
        
        Args:
            parameters: Validated input parameters
                - brandid: Integer brand ID
                - feedback_text: String feedback text
                - metadata_version: Optional integer version (defaults to latest)
            
        Returns:
            Dictionary containing:
                - feedback_id: Unique feedback identifier (UUID)
                - stored: Boolean indicating storage success
                - storage_location: S3 key where feedback was stored
                - category: Feedback category identified
                - issues_identified: List of issues found
                - misclassified_combos: List of combo IDs mentioned
        """
        brandid = parameters["brandid"]
        feedback_text = parameters["feedback_text"]
        
        # Get metadata version (use latest if not provided)
        metadata_version = parameters.get("metadata_version")
        if metadata_version is None:
            metadata_version = self.get_latest_metadata_version(brandid)
        
        self.logger.info(
            f"Processing feedback for brand {brandid}, version {metadata_version}"
        )
        
        # Parse feedback using feedback_processing agent tools
        try:
            parsed_feedback = parse_feedback(feedback_text, brandid)
        except Exception as e:
            raise BackendServiceError(
                f"Failed to parse feedback: {str(e)}",
                details=f"Feedback text: {feedback_text[:100]}...",
                suggestion="Check feedback text format and try again",
            )
        
        # Check for parsing errors
        if "error" in parsed_feedback:
            raise UserInputError(
                f"Feedback parsing error: {parsed_feedback['error']}",
                suggestion="Provide valid feedback text",
            )
        
        # Prepare complete feedback record
        feedback_record = {
            "feedback_id": parsed_feedback["feedback_id"],
            "brandid": brandid,
            "metadata_version": metadata_version,
            "feedback_text": feedback_text,
            "category": parsed_feedback["category"],
            "issues_identified": parsed_feedback["issues_identified"],
            "misclassified_combos": parsed_feedback["misclassified_combos"],
            "submitted_at": parsed_feedback["timestamp"],
            "submitted_by": "conversational_interface",  # Could be enhanced with user identity
        }
        
        # Store to both S3 and Athena using dual storage (this will be retried if it fails)
        s3_key = self.store_feedback(feedback_record, brandid)
        
        # Return success response
        return {
            "feedback_id": feedback_record["feedback_id"],
            "stored": True,
            "storage_location": f"s3://brand-generator-rwrd-023-eu-west-1/{s3_key}",
            "category": feedback_record["category"],
            "issues_identified": feedback_record["issues_identified"],
            "misclassified_combos": feedback_record["misclassified_combos"],
        }
    
    def is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable.
        
        Args:
            error: Exception that occurred
            
        Returns:
            True if error is retryable (backend service errors), False otherwise
        """
        # Retry backend service errors (S3, Athena failures)
        # Don't retry user input errors
        return isinstance(error, BackendServiceError)


# Lambda handler entry point
handler_instance = FeedbackSubmissionHandler()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point.
    
    Args:
        event: Lambda event dictionary
        context: Lambda context object
        
    Returns:
        Standardized response dictionary
    """
    return handler_instance.handle(event, context)
