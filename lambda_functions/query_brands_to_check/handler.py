"""Lambda handler for querying brands_to_check table.

This tool queries the brands_to_check Athena table to find brands that need
to be processed. It supports filtering by status and pagination.

Requirements: 7.1, 2.1, 2.2, 2.3
"""

from typing import Any, Dict

from shared.storage.athena_client import AthenaClient
from shared.utils.base_handler import BaseToolHandler
from shared.utils.error_handler import UserInputError


class QueryBrandsToCheckHandler(BaseToolHandler):
    """Handler for query_brands_to_check tool."""
    
    def __init__(self):
        """Initialize handler."""
        super().__init__("query_brands_to_check")
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
        # Validate limit if provided
        if "limit" in parameters:
            limit = parameters["limit"]
            if not isinstance(limit, int):
                raise UserInputError(
                    f"Parameter 'limit' must be an integer, got {type(limit).__name__}",
                    suggestion="Provide a positive integer for limit (e.g., 10, 50, 100)",
                )
            if limit <= 0:
                raise UserInputError(
                    f"Parameter 'limit' must be positive, got {limit}",
                    suggestion="Provide a positive integer for limit (e.g., 10, 50, 100)",
                )
            if limit > 1000:
                raise UserInputError(
                    f"Parameter 'limit' cannot exceed 1000, got {limit}",
                    suggestion="Use a limit of 1000 or less for better performance",
                )
        
        # Validate status if provided
        if "status" in parameters:
            status = parameters["status"]
            if not isinstance(status, str):
                raise UserInputError(
                    f"Parameter 'status' must be a string, got {type(status).__name__}",
                    suggestion="Provide a status string (e.g., 'unprocessed', 'processed')",
                )
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute query against brands_to_check table.
        
        Args:
            parameters: Validated input parameters
                - status (optional): Filter by status
                - limit (optional): Maximum number of results (default: 10)
            
        Returns:
            Dictionary containing:
                - brands: List of brand records
                - total_count: Total number of matching brands
        """
        # Extract parameters
        status = parameters.get("status")
        limit = parameters.get("limit", 10)
        
        # Build WHERE clause
        where_clause = None
        if status:
            where_clause = f"status = '{status}'"
        
        # Get total count
        total_count = self.athena_client.get_table_count(
            "brands_to_check", where=where_clause
        )
        
        # Query brands
        brands = self.athena_client.query_table(
            table_name="brands_to_check",
            columns="brandid, brandname, status, sector",
            where=where_clause,
            limit=limit,
        )
        
        return {
            "brands": brands,
            "total_count": total_count,
        }


# Lambda handler entry point
handler_instance = QueryBrandsToCheckHandler()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point.
    
    Args:
        event: Lambda event dictionary
        context: Lambda context object
        
    Returns:
        Standardized response dictionary
    """
    return handler_instance.handle(event, context)
