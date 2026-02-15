"""Lambda handler for querying brands_to_check table.

This tool queries the brand_processing_status DynamoDB table to find brands that need
to be processed. It supports filtering by status and pagination.

Requirements: 7.1, 2.1, 2.2, 2.3
"""

from typing import Any, Dict

from shared.storage.dynamodb_client import DynamoDBClient
from shared.utils.base_handler import BaseToolHandler
from shared.utils.error_handler import UserInputError


class QueryBrandsToCheckHandler(BaseToolHandler):
    """Handler for query_brands_to_check tool."""
    
    def __init__(self):
        """Initialize handler."""
        super().__init__("query_brands_to_check")
        self.dynamodb_client = DynamoDBClient(
            table_name="brand_processing_status_dev",
            region="eu-west-1",
        )
    
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
        """Execute query against brand_processing_status DynamoDB table.
        
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
        brand_status = parameters.get("status")  # Map "status" parameter to "brand_status"
        limit = parameters.get("limit", 10)
        
        try:
            # Query brands from DynamoDB
            brands = self.dynamodb_client.query_brands_by_status(brand_status=brand_status, limit=limit)
            
            # Get status counts for total_count
            status_counts = self.dynamodb_client.get_status_counts()
            
            if brand_status:
                # Return count for specific status
                total_count = status_counts.get(brand_status, 0)
            else:
                # Return total count across all statuses
                total_count = sum(status_counts.values())
            
            # Convert DynamoDB items to expected format
            formatted_brands = []
            for brand in brands:
                formatted_brand = {
                    'brandid': int(brand['brandid']),
                    'brandname': brand.get('brandname', f"Brand {brand['brandid']}"),
                    'status': brand.get('brand_status', 'unprocessed'),
                    'sector': brand.get('sector', 'Unknown'),
                }
                formatted_brands.append(formatted_brand)
            
            return {
                "brands": formatted_brands,
                "total_count": total_count,
            }
            
        except Exception as e:
            # Log the error and re-raise with context
            self.logger.error(f"Failed to query brands: {e}")
            raise Exception(f"Failed to query brand processing status: {e}")


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
