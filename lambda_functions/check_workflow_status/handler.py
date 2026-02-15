"""Lambda handler for querying Step Functions workflow status.

This tool queries the status of Step Functions workflow executions. It validates
execution ARNs, retrieves execution details, and formats the response with status,
timing information, and error details if the execution failed.

Requirements: 7.3, 2.4
"""

import json
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

from shared.storage.dual_storage import DualStorageClient
from shared.utils.base_handler import BaseToolHandler
from shared.utils.error_handler import BackendServiceError, UserInputError


class CheckWorkflowStatusHandler(BaseToolHandler):
    """Handler for check_workflow_status tool."""
    
    def __init__(self):
        """Initialize handler."""
        super().__init__("check_workflow_status")
        
        # Initialize Step Functions client
        self.sfn_client = boto3.client("stepfunctions", region_name="eu-west-1")
        
        # Initialize dual storage client for workflow execution logging
        self.dual_storage = DualStorageClient(
            bucket="brand-generator-rwrd-023-eu-west-1",
            database="brand_metadata_generator_db",
            region="eu-west-1",
        )
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate input parameters.
        
        Args:
            parameters: Input parameters
            
        Raises:
            UserInputError: If parameters are invalid
        """
        # Validate execution_arn is present
        if "execution_arn" not in parameters:
            raise UserInputError(
                "Parameter 'execution_arn' is required",
                suggestion="Provide the execution ARN returned when the workflow was started",
            )
        
        execution_arn = parameters["execution_arn"]
        
        # Validate execution_arn type
        if not isinstance(execution_arn, str):
            raise UserInputError(
                f"Parameter 'execution_arn' must be a string, got {type(execution_arn).__name__}",
                suggestion="Provide the execution ARN as a string",
            )
        
        # Validate execution_arn is not empty
        if not execution_arn.strip():
            raise UserInputError(
                "Parameter 'execution_arn' cannot be empty",
                suggestion="Provide a valid execution ARN",
            )
        
        # Basic ARN format validation
        if not execution_arn.startswith("arn:aws:states:"):
            raise UserInputError(
                f"Invalid execution ARN format: {execution_arn}",
                suggestion="Execution ARN should start with 'arn:aws:states:'",
            )
    
    def parse_execution_output(self, output_str: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parse execution output JSON string.
        
        Args:
            output_str: JSON string from execution output
            
        Returns:
            Parsed output dictionary or None if parsing fails
        """
        if not output_str:
            return None
        
        try:
            return json.loads(output_str)
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse execution output: {str(e)}")
            return {"raw_output": output_str}
    
    def format_execution_details(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        """Format execution details for response.
        
        Args:
            execution: Raw execution details from describe_execution
            
        Returns:
            Formatted execution details
        """
        # Extract basic status information
        result = {
            "status": execution["status"],
            "start_time": execution["startDate"].isoformat(),
        }
        
        # Add stop time if execution has completed
        if "stopDate" in execution:
            result["stop_time"] = execution["stopDate"].isoformat()
        
        # Add output if execution succeeded
        if execution["status"] == "SUCCEEDED" and "output" in execution:
            result["output"] = self.parse_execution_output(execution["output"])
        
        # Add error information if execution failed
        if execution["status"] in ["FAILED", "TIMED_OUT", "ABORTED"]:
            if "error" in execution:
                result["error"] = execution["error"]
            if "cause" in execution:
                result["cause"] = execution["cause"]
        
        # Add execution name for reference
        if "name" in execution:
            result["execution_name"] = execution["name"]
        
        # Add state machine ARN
        if "stateMachineArn" in execution:
            result["state_machine_arn"] = execution["stateMachineArn"]
        
        # Parse and add input if available
        if "input" in execution:
            parsed_input = self.parse_execution_output(execution["input"])
            if parsed_input:
                result["input"] = parsed_input
        
        return result
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Query Step Functions execution status.
        
        Args:
            parameters: Validated input parameters
                - execution_arn: Step Functions execution ARN
            
        Returns:
            Dictionary containing:
                - status: Execution status (RUNNING|SUCCEEDED|FAILED|TIMED_OUT|ABORTED)
                - start_time: ISO 8601 timestamp
                - stop_time: ISO 8601 timestamp (if completed)
                - output: Execution output (if succeeded)
                - error: Error message (if failed)
                - cause: Error cause details (if failed)
                - execution_name: Name of the execution
                - state_machine_arn: ARN of the state machine
                - input: Execution input
        """
        execution_arn = parameters["execution_arn"]
        
        try:
            # Query execution status
            response = self.sfn_client.describe_execution(
                executionArn=execution_arn
            )
            
            # Format execution details
            formatted_details = self.format_execution_details(response)
            
            # Log workflow execution status to dual storage if execution is complete
            status = response["status"]
            if status in ["SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]:
                try:
                    # Extract brandid from input if available
                    brandid = None
                    if "input" in response:
                        parsed_input = self.parse_execution_output(response["input"])
                        if parsed_input and "brandid" in parsed_input:
                            brandid = parsed_input["brandid"]
                    
                    # Calculate duration if stop time is available
                    duration_seconds = None
                    if "stopDate" in response and "startDate" in response:
                        duration = response["stopDate"] - response["startDate"]
                        duration_seconds = int(duration.total_seconds())
                    
                    # Prepare execution data for logging
                    execution_data = {
                        "execution_arn": execution_arn,
                        "status": status,
                        "start_time": response["startDate"].isoformat(),
                    }
                    
                    if brandid:
                        execution_data["brandid"] = brandid
                    
                    if "stopDate" in response:
                        execution_data["stop_time"] = response["stopDate"].isoformat()
                    
                    if duration_seconds is not None:
                        execution_data["duration_seconds"] = duration_seconds
                    
                    if "input" in response:
                        execution_data["input_data"] = response["input"]
                    
                    if status == "SUCCEEDED" and "output" in response:
                        execution_data["output_data"] = response["output"]
                    
                    if status in ["FAILED", "TIMED_OUT", "ABORTED"]:
                        error_parts = []
                        if "error" in response:
                            error_parts.append(response["error"])
                        if "cause" in response:
                            error_parts.append(response["cause"])
                        if error_parts:
                            execution_data["error_message"] = " - ".join(error_parts)
                    
                    # Write to dual storage
                    self.dual_storage.write_workflow_execution(execution_data)
                    self.logger.info(f"Logged workflow execution completion: {execution_arn} - {status}")
                    
                except Exception as log_error:
                    # Log error but don't fail the status check
                    self.logger.error(f"Failed to log workflow execution status: {str(log_error)}")
            
            return formatted_details
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            
            if error_code == "ExecutionDoesNotExist":
                raise UserInputError(
                    f"Execution not found: {execution_arn}",
                    suggestion="Verify the execution ARN is correct and the execution exists",
                )
            elif error_code == "InvalidArn":
                raise UserInputError(
                    f"Invalid execution ARN: {execution_arn}",
                    suggestion="Provide a valid Step Functions execution ARN",
                )
            elif error_code == "AccessDeniedException":
                raise BackendServiceError(
                    "Permission denied to query execution status",
                    details=error_message,
                    suggestion="Contact administrator to verify IAM permissions",
                )
            else:
                raise BackendServiceError(
                    f"Failed to query execution status: {error_message}",
                    details=f"Error code: {error_code}",
                    suggestion="Check Step Functions service status or contact administrator",
                )


# Lambda handler entry point
handler_instance = CheckWorkflowStatusHandler()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point.
    
    Args:
        event: Lambda event dictionary
        context: Lambda context object
        
    Returns:
        Standardized response dictionary
    """
    return handler_instance.handle(event, context)
