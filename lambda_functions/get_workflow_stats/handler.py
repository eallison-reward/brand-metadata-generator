"""Lambda function for getting workflow statistics.

This tool retrieves workflow execution statistics from the workflow_executions table
for the Conversational Interface Agent. Supports time period filtering and calculates
success rates and averages.
"""

import sys
import os
from typing import Any, Dict
from datetime import datetime, timedelta

# Add shared directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.storage.athena_client import AthenaClient
from shared.utils.base_handler import BaseToolHandler
from shared.utils.error_handler import UserInputError, BackendServiceError


class GetWorkflowStatsHandler(BaseToolHandler):
    """Handler for getting workflow statistics from Athena."""
    
    def __init__(self):
        """Initialize handler with Athena client."""
        super().__init__("get_workflow_stats")
        
        # Get configuration from environment
        database = os.environ.get("ATHENA_DATABASE", "brand_metadata_generator_db")
        region = os.environ.get("AWS_REGION", "eu-west-1")
        output_location = os.environ.get(
            "ATHENA_OUTPUT_LOCATION",
            "s3://brand-generator-rwrd-023-eu-west-1/query-results/"
        )
        
        # Initialize Athena client
        self.athena_client = AthenaClient(
            database=database,
            region=region,
            output_location=output_location
        )
    
    def get_required_params(self) -> list[str]:
        """Get list of required parameters.
        
        Returns:
            List with time_period as required parameter
        """
        return ["time_period"]
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate input parameters.
        
        Args:
            parameters: Input parameters with time_period
            
        Raises:
            UserInputError: If parameters are invalid
        """
        # Validate required parameters
        self.validate_required_params(parameters)
        
        # Validate time_period
        time_period = parameters.get("time_period")
        valid_periods = ["last_hour", "last_day", "last_week"]
        
        if time_period not in valid_periods:
            raise UserInputError(
                f"time_period must be one of {valid_periods}, got: {time_period}",
                suggestion=f"Use one of: {', '.join(valid_periods)}"
            )
        
        # Validate include_details if provided
        include_details = parameters.get("include_details")
        if include_details is not None and not isinstance(include_details, bool):
            raise UserInputError(
                f"include_details must be a boolean, got: {include_details}",
                suggestion="Provide include_details as true or false"
            )
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow statistics query.
        
        Args:
            parameters: Validated parameters with time_period
            
        Returns:
            Dictionary containing workflow statistics
            
        Raises:
            BackendServiceError: If Athena query fails
        """
        time_period = parameters.get("time_period")
        include_details = parameters.get("include_details", False)
        
        try:
            # Calculate time threshold
            time_threshold = self._calculate_time_threshold(time_period)
            
            # Build and execute statistics query
            self.logger.info(f"Executing workflow stats query for {time_period}")
            query = self._build_stats_query(time_threshold)
            results = self.athena_client.execute_query(query)
            
            # Parse statistics
            stats = self._parse_statistics(results, time_period)
            
            # Add details if requested
            if include_details:
                details_query = self._build_details_query(time_threshold)
                details_results = self.athena_client.execute_query(details_query)
                stats["execution_details"] = self._format_execution_details(details_results)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get workflow statistics: {str(e)}")
            raise BackendServiceError(
                f"Failed to query workflow statistics from Athena: {str(e)}",
                suggestion="Check that the workflow_executions table exists and is accessible"
            )
    
    def _calculate_time_threshold(self, time_period: str) -> str:
        """Calculate time threshold for filtering.
        
        Args:
            time_period: Time period (last_hour, last_day, last_week)
            
        Returns:
            ISO 8601 timestamp string for filtering
        """
        now = datetime.utcnow()
        
        if time_period == "last_hour":
            threshold = now - timedelta(hours=1)
        elif time_period == "last_day":
            threshold = now - timedelta(days=1)
        elif time_period == "last_week":
            threshold = now - timedelta(weeks=1)
        else:
            # Default to last day
            threshold = now - timedelta(days=1)
        
        return threshold.isoformat()
    
    def _build_stats_query(self, time_threshold: str) -> str:
        """Build Athena query for workflow statistics.
        
        Args:
            time_threshold: ISO 8601 timestamp for filtering
            
        Returns:
            SQL query string
        """
        query = f"""
        SELECT 
            COUNT(*) as total_executions,
            SUM(CASE WHEN status = 'SUCCEEDED' THEN 1 ELSE 0 END) as successful,
            SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status = 'RUNNING' THEN 1 ELSE 0 END) as running,
            AVG(CASE WHEN duration_seconds IS NOT NULL THEN duration_seconds ELSE 0 END) as avg_duration,
            COUNT(DISTINCT brandid) as brands_processed
        FROM workflow_executions
        WHERE start_time >= TIMESTAMP '{time_threshold}'
        """
        
        return query
    
    def _build_details_query(self, time_threshold: str) -> str:
        """Build query for execution details.
        
        Args:
            time_threshold: ISO 8601 timestamp for filtering
            
        Returns:
            SQL query string
        """
        query = f"""
        SELECT 
            execution_arn,
            brandid,
            status,
            start_time,
            stop_time,
            duration_seconds,
            error_message
        FROM workflow_executions
        WHERE start_time >= TIMESTAMP '{time_threshold}'
        ORDER BY start_time DESC
        LIMIT 50
        """
        
        return query
    
    def _parse_statistics(self, results: list, time_period: str) -> Dict[str, Any]:
        """Parse statistics from query results.
        
        Args:
            results: Query results from Athena
            time_period: Time period for context
            
        Returns:
            Dictionary with formatted statistics
        """
        if not results or len(results) == 0:
            return {
                "time_period": time_period,
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "running": 0,
                "success_rate": 0.0,
                "average_duration_seconds": 0.0,
                "brands_processed": 0
            }
        
        row = results[0]
        
        total = row.get("total_executions", 0)
        successful = row.get("successful", 0)
        failed = row.get("failed", 0)
        running = row.get("running", 0)
        avg_duration = row.get("avg_duration", 0.0)
        brands_processed = row.get("brands_processed", 0)
        
        # Calculate success rate
        # Only count completed executions (successful + failed)
        completed = successful + failed
        success_rate = (successful / completed * 100) if completed > 0 else 0.0
        
        return {
            "time_period": time_period,
            "total_executions": total,
            "successful": successful,
            "failed": failed,
            "running": running,
            "success_rate": round(success_rate, 2),
            "average_duration_seconds": round(avg_duration, 2),
            "brands_processed": brands_processed
        }
    
    def _format_execution_details(self, results: list) -> list:
        """Format execution details for presentation.
        
        Args:
            results: Query results from Athena
            
        Returns:
            List of formatted execution dictionaries
        """
        details = []
        
        for row in results:
            detail = {
                "execution_arn": row.get("execution_arn", ""),
                "brandid": row.get("brandid", 0),
                "status": row.get("status", "UNKNOWN"),
                "start_time": row.get("start_time", ""),
                "stop_time": row.get("stop_time", ""),
                "duration_seconds": row.get("duration_seconds", 0),
            }
            
            # Only include error message if present
            error_message = row.get("error_message")
            if error_message:
                detail["error_message"] = error_message
            
            details.append(detail)
        
        return details


# Lambda handler entry point
handler_instance = GetWorkflowStatsHandler()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point.
    
    Args:
        event: Lambda event with parameters
        context: Lambda context
        
    Returns:
        Standardized response dictionary
    """
    return handler_instance.handle(event, context)
