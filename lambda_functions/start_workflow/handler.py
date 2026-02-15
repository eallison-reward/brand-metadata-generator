"""Lambda handler for starting Step Functions workflows.

This tool starts Step Functions workflows for brand processing. It supports
starting workflows for single or multiple brands, validates brand IDs,
generates unique execution names, and returns execution ARNs.

Requirements: 7.2, 2.1, 2.2, 2.3, 2.6
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Union

import boto3
from botocore.exceptions import ClientError

from shared.storage.dynamodb_client import DynamoDBClient
from shared.storage.dual_storage import DualStorageClient
from shared.utils.base_handler import BaseToolHandler
from shared.utils.error_handler import BackendServiceError, UserInputError


class StartWorkflowHandler(BaseToolHandler):
    """Handler for start_workflow tool."""
    
    def __init__(self):
        """Initialize handler."""
        super().__init__("start_workflow")
        
        # Initialize Step Functions client
        self.sfn_client = boto3.client("stepfunctions", region_name="eu-west-1")
        
        # Initialize DynamoDB client for brand status tracking
        self.dynamodb_client = DynamoDBClient(
            table_name="brand_processing_status_dev",
            region="eu-west-1",
        )
        
        # Initialize dual storage client for workflow execution logging
        self.dual_storage = DualStorageClient(
            bucket="brand-generator-rwrd-023-eu-west-1",
            database="brand_metadata_generator_db",
            region="eu-west-1",
        )
        
        # Get Step Functions workflow ARN from environment
        self.state_machine_arn = os.environ.get("STATE_MACHINE_ARN")
        if not self.state_machine_arn:
            raise ValueError("STATE_MACHINE_ARN environment variable not set")
    
    def handle(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Override handle to return direct response format for Bedrock Agent.
        
        Args:
            event: Lambda event dictionary
            context: Lambda context object
            
        Returns:
            Direct response dictionary (not wrapped in success/data)
        """
        try:
            # Extract parameters directly from event
            parameters = event if isinstance(event, dict) else {}
            
            # Validate parameters
            self.validate_parameters(parameters)
            
            # Execute tool logic
            result = self.execute(parameters)
            
            # Return direct result (not wrapped)
            return result
            
        except Exception as e:
            # Log the error and re-raise
            self.logger.error(f"Handler error: {e}")
            raise
    
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
                suggestion="Provide a brand ID (integer) or list of brand IDs to process",
            )
        
        brandid = parameters["brandid"]
        
        # Validate brandid type (can be int or list of ints)
        if isinstance(brandid, int):
            if brandid <= 0:
                raise UserInputError(
                    f"Brand ID must be positive, got {brandid}",
                    suggestion="Provide a valid positive brand ID",
                )
        elif isinstance(brandid, list):
            if not brandid:
                raise UserInputError(
                    "Brand ID list cannot be empty",
                    suggestion="Provide at least one brand ID to process",
                )
            for bid in brandid:
                if not isinstance(bid, int):
                    raise UserInputError(
                        f"All brand IDs must be integers, got {type(bid).__name__}",
                        suggestion="Provide a list of integer brand IDs",
                    )
                if bid <= 0:
                    raise UserInputError(
                        f"All brand IDs must be positive, got {bid}",
                        suggestion="Provide valid positive brand IDs",
                    )
        else:
            raise UserInputError(
                f"Parameter 'brandid' must be an integer or list of integers, got {type(brandid).__name__}",
                suggestion="Provide a brand ID (integer) or list of brand IDs",
            )
        
        # Validate execution_name if provided
        if "execution_name" in parameters:
            execution_name = parameters["execution_name"]
            if not isinstance(execution_name, str):
                raise UserInputError(
                    f"Parameter 'execution_name' must be a string, got {type(execution_name).__name__}",
                    suggestion="Provide a string for execution name",
                )
            if not execution_name.strip():
                raise UserInputError(
                    "Parameter 'execution_name' cannot be empty",
                    suggestion="Provide a non-empty execution name or omit to auto-generate",
                )
    
    def verify_brand_exists(self, brandid: int) -> bool:
        """Verify that a brand exists in the brand_processing_status table.
        
        Args:
            brandid: Brand ID to verify
            
        Returns:
            True if brand exists, False otherwise
        """
        try:
            brand = self.dynamodb_client.get_brand_by_id(brandid)
            return brand is not None
        except Exception as e:
            self.logger.warning(f"Failed to verify brand {brandid}: {str(e)}")
            # If verification fails, we'll let the workflow handle it
            return True
    
    def generate_execution_name(self, brandid: int, base_name: str = None) -> str:
        """Generate a unique execution name.
        
        Args:
            brandid: Brand ID being processed
            base_name: Optional base name for the execution
            
        Returns:
            Unique execution name
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")[:20]  # Truncate microseconds
        
        if base_name:
            # Sanitize base name (Step Functions has restrictions)
            sanitized = "".join(c if c.isalnum() or c in "-_" else "-" for c in base_name)
            return f"{sanitized}-brand{brandid}-{timestamp}"
        else:
            return f"brand{brandid}-{timestamp}"
    
    def start_single_workflow(
        self, brandid: int, execution_name: str = None
    ) -> Dict[str, Any]:
        """Start workflow for a single brand.
        
        Args:
            brandid: Brand ID to process
            execution_name: Optional execution name
            
        Returns:
            Dictionary with execution details
            
        Raises:
            UserInputError: If brand doesn't exist
            BackendServiceError: If workflow start fails
        """
        # Verify brand exists
        if not self.verify_brand_exists(brandid):
            raise UserInputError(
                f"Brand ID {brandid} not found in brand_processing_status table",
                suggestion="Verify the brand ID exists or add it to the brand_processing_status table",
            )
        
        # Generate execution name if not provided
        if not execution_name:
            execution_name = self.generate_execution_name(brandid)
        else:
            # Ensure execution name includes brand ID and timestamp for uniqueness
            execution_name = self.generate_execution_name(brandid, execution_name)
        
        # Prepare workflow input
        workflow_input = {
            "action": "start_workflow",
            "brandid": brandid,
            "config": {
                "max_iterations": 5,
                "confidence_threshold": 0.75,
                "enable_confirmation": True,
                "enable_tiebreaker": True,
            },
        }
        
        try:
            # Start Step Functions execution
            response = self.sfn_client.start_execution(
                stateMachineArn=self.state_machine_arn,
                name=execution_name,
                input=json.dumps(workflow_input),
            )
            
            execution_arn = response["executionArn"]
            start_time = response["startDate"].isoformat()
            
            # Update brand status to "processing" in DynamoDB
            try:
                self.dynamodb_client.update_brand_status(
                    brandid=brandid,
                    brand_status="processing",
                    workflow_execution_arn=execution_arn
                )
                self.logger.info(f"Updated brand {brandid} status to processing")
            except Exception as status_error:
                # Log error but don't fail the workflow start
                self.logger.error(f"Failed to update brand status: {str(status_error)}")
            
            # Log workflow execution start to dual storage
            try:
                execution_data = {
                    "execution_arn": execution_arn,
                    "brandid": brandid,
                    "status": "RUNNING",
                    "start_time": start_time,
                    "input_data": json.dumps(workflow_input),
                }
                self.dual_storage.write_workflow_execution(execution_data)
                self.logger.info(f"Logged workflow execution start for brand {brandid}: {execution_arn}")
            except Exception as log_error:
                # Log error but don't fail the workflow start
                self.logger.error(f"Failed to log workflow execution start: {str(log_error)}")
            
            return {
                "brandid": brandid,
                "execution_arn": execution_arn,
                "start_time": start_time,
            }
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            
            if error_code == "ExecutionAlreadyExists":
                raise UserInputError(
                    f"Workflow execution '{execution_name}' already exists",
                    suggestion="Use a different execution name or check the status of the existing execution",
                )
            elif error_code == "InvalidArn":
                raise BackendServiceError(
                    f"Invalid Step Functions ARN: {self.state_machine_arn}",
                    details=error_message,
                    suggestion="Contact administrator to verify Step Functions configuration",
                )
            else:
                raise BackendServiceError(
                    f"Failed to start workflow: {error_message}",
                    details=f"Error code: {error_code}",
                    suggestion="Check Step Functions service status or contact administrator",
                )
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow start for one or more brands.
        
        Args:
            parameters: Validated input parameters
                - brandid: Integer or list of integers
                - execution_name: Optional base name for executions
            
        Returns:
            Dictionary containing:
                - executions: List of execution details
                - success: Boolean indicating overall success
        """
        brandid = parameters["brandid"]
        execution_name = parameters.get("execution_name")
        
        # Handle single brand
        if isinstance(brandid, int):
            execution = self.start_single_workflow(brandid, execution_name)
            return {
                "executions": [execution],
                "success": True,
            }
        
        # Handle multiple brands
        executions = []
        errors = []
        
        for bid in brandid:
            try:
                execution = self.start_single_workflow(bid, execution_name)
                executions.append(execution)
            except (UserInputError, BackendServiceError) as e:
                errors.append({
                    "brandid": bid,
                    "error": str(e),
                })
                self.logger.error(f"Failed to start workflow for brand {bid}: {str(e)}")
        
        # If all failed, raise error
        if not executions and errors:
            raise BackendServiceError(
                f"Failed to start workflows for all {len(errors)} brands",
                details=f"Errors: {errors}",
                suggestion="Check brand IDs and Step Functions service status",
            )
        
        # Return results (partial success is OK)
        result = {
            "executions": executions,
            "success": len(executions) > 0,
        }
        
        if errors:
            result["errors"] = errors
            result["partial_success"] = True
        
        return result


# Lambda handler entry point
handler_instance = StartWorkflowHandler()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point.
    
    Args:
        event: Lambda event dictionary
        context: Lambda context object
        
    Returns:
        Standardized response dictionary
    """
    return handler_instance.handle(event, context)
