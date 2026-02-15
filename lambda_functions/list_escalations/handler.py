"""Lambda function for listing escalations.

This tool retrieves brands awaiting human review from the escalations table
for the Conversational Interface Agent. Supports filtering, sorting, and pagination.
"""

import sys
import os
from typing import Any, Dict, List

# Add shared directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.storage.athena_client import AthenaClient
from shared.utils.base_handler import BaseToolHandler
from shared.utils.error_handler import UserInputError, BackendServiceError


class ListEscalationsHandler(BaseToolHandler):
    """Handler for listing escalations from Athena."""
    
    def __init__(self):
        """Initialize handler with Athena client."""
        super().__init__("list_escalations")
        
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
            Empty list (all parameters are optional)
        """
        return []
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate input parameters.
        
        Args:
            parameters: Input parameters with optional limit and sort_by
            
        Raises:
            UserInputError: If parameters are invalid
        """
        # Validate limit if provided
        limit = parameters.get("limit")
        if limit is not None:
            if not isinstance(limit, int):
                try:
                    parameters["limit"] = int(limit)
                except (ValueError, TypeError):
                    raise UserInputError(
                        f"limit must be an integer, got: {limit}",
                        suggestion="Provide a valid limit as an integer"
                    )
            
            if parameters["limit"] <= 0:
                raise UserInputError(
                    f"limit must be positive, got: {parameters['limit']}",
                    suggestion="Provide a positive limit value"
                )
            
            if parameters["limit"] > 100:
                raise UserInputError(
                    f"limit cannot exceed 100, got: {parameters['limit']}",
                    suggestion="Provide a limit value between 1 and 100"
                )
        
        # Validate sort_by if provided
        sort_by = parameters.get("sort_by")
        if sort_by is not None:
            valid_sort_fields = ["escalated_at", "confidence_score", "brandid", "brandname"]
            if sort_by not in valid_sort_fields:
                raise UserInputError(
                    f"sort_by must be one of {valid_sort_fields}, got: {sort_by}",
                    suggestion=f"Use one of: {', '.join(valid_sort_fields)}"
                )
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute escalation listing query.
        
        Args:
            parameters: Validated parameters with optional limit and sort_by
            
        Returns:
            Dictionary containing escalations list and total count
            
        Raises:
            BackendServiceError: If Athena query fails
        """
        limit = parameters.get("limit", 10)
        sort_by = parameters.get("sort_by", "escalated_at")
        
        try:
            # Build query for unresolved escalations
            query = self._build_query(sort_by, limit)
            
            # Execute query
            self.logger.info(f"Executing escalations query with limit={limit}, sort_by={sort_by}")
            results = self.athena_client.execute_query(query)
            
            # Get total count of unresolved escalations
            total_count = self._get_total_count()
            
            # Format results
            escalations = self._format_escalations(results)
            
            return {
                "escalations": escalations,
                "total_count": total_count,
                "returned_count": len(escalations),
                "limit": limit,
                "sort_by": sort_by
            }
            
        except Exception as e:
            self.logger.error(f"Failed to list escalations: {str(e)}")
            raise BackendServiceError(
                f"Failed to query escalations from Athena: {str(e)}",
                suggestion="Check that the escalations table exists and is accessible"
            )
    
    def _build_query(self, sort_by: str, limit: int) -> str:
        """Build Athena query for listing escalations.
        
        Args:
            sort_by: Field to sort by
            limit: Maximum number of results
            
        Returns:
            SQL query string
        """
        # Query for unresolved escalations (status is pending or null)
        query = """
        SELECT 
            escalation_id,
            brandid,
            brandname,
            reason,
            confidence_score,
            escalated_at,
            status
        FROM escalations
        WHERE status = 'pending' OR status IS NULL OR resolved_at IS NULL
        """
        
        # Add sorting
        # Default to descending for escalated_at (most recent first)
        # Ascending for confidence_score (lowest confidence first)
        if sort_by == "escalated_at":
            query += " ORDER BY escalated_at DESC"
        elif sort_by == "confidence_score":
            query += " ORDER BY confidence_score ASC"
        elif sort_by == "brandid":
            query += " ORDER BY brandid ASC"
        elif sort_by == "brandname":
            query += " ORDER BY brandname ASC"
        
        # Add limit
        query += f" LIMIT {limit}"
        
        return query
    
    def _get_total_count(self) -> int:
        """Get total count of unresolved escalations.
        
        Returns:
            Total number of unresolved escalations
        """
        try:
            count_query = """
            SELECT COUNT(*) as count
            FROM escalations
            WHERE status = 'pending' OR status IS NULL OR resolved_at IS NULL
            """
            
            results = self.athena_client.execute_query(count_query)
            
            if results and len(results) > 0:
                return results[0].get("count", 0)
            
            return 0
            
        except Exception as e:
            self.logger.warning(f"Failed to get total escalation count: {str(e)}")
            return 0
    
    def _format_escalations(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format escalation results for presentation.
        
        Args:
            results: Raw query results from Athena
            
        Returns:
            List of formatted escalation dictionaries
        """
        escalations = []
        
        for row in results:
            escalation = {
                "escalation_id": row.get("escalation_id", ""),
                "brandid": row.get("brandid", 0),
                "brandname": row.get("brandname", "Unknown"),
                "reason": row.get("reason", ""),
                "confidence_score": row.get("confidence_score", 0.0),
                "escalated_at": row.get("escalated_at", ""),
                "status": row.get("status", "pending")
            }
            
            escalations.append(escalation)
        
        return escalations


# Lambda handler entry point
handler_instance = ListEscalationsHandler()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point.
    
    Args:
        event: Lambda event with parameters
        context: Lambda context
        
    Returns:
        Standardized response dictionary
    """
    return handler_instance.handle(event, context)
