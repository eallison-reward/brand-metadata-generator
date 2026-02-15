"""Lambda function for executing Athena queries.

This tool executes parameterized Athena queries for the Conversational Interface Agent.
Supports predefined query templates and custom SQL execution with pagination.
"""

import sys
import os
from typing import Any, Dict, List, Optional

# Add shared directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.storage.athena_client import AthenaClient
from shared.utils.base_handler import BaseToolHandler
from shared.utils.error_handler import UserInputError, BackendServiceError


# Predefined query templates
QUERY_TEMPLATES = {
    "brands_by_confidence": """
        SELECT brandid, brandname, confidence_score, generated_at
        FROM generated_metadata
        WHERE confidence_score >= {min_confidence} 
        AND confidence_score <= {max_confidence}
        ORDER BY confidence_score DESC
    """,
    "brands_by_category": """
        SELECT brandid, brandname, sector, confidence_score
        FROM generated_metadata
        WHERE sector = '{sector}'
        ORDER BY brandname
    """,
    "recent_workflows": """
        SELECT execution_arn, brandid, status, start_time, duration_seconds
        FROM workflow_executions
        WHERE start_time >= date_add('day', -{days}, current_timestamp)
        ORDER BY start_time DESC
    """,
    "escalations_pending": """
        SELECT escalation_id, brandid, brandname, reason, confidence_score, escalated_at
        FROM escalations
        WHERE status = 'pending'
        ORDER BY escalated_at DESC
    """,
    "low_confidence_brands": """
        SELECT brandid, brandname, confidence_score, generated_at
        FROM generated_metadata
        WHERE confidence_score < {threshold}
        ORDER BY confidence_score ASC
    """,
    "brands_by_status": """
        SELECT brandid, brandname, status, sector
        FROM brands_to_check
        WHERE status = '{status}'
        ORDER BY brandid
    """,
}


class ExecuteAthenaQueryHandler(BaseToolHandler):
    """Handler for executing Athena queries."""
    
    def __init__(self):
        """Initialize handler with Athena client."""
        super().__init__("execute_athena_query")
        
        # Get configuration from environment
        database = os.environ.get("ATHENA_DATABASE", "brand_metadata_generator_db")
        region = os.environ.get("AWS_REGION", "eu-west-1")
        bucket = os.environ.get("S3_BUCKET", "brand-generator-rwrd-023-eu-west-1")
        output_location = f"s3://{bucket}/query-results/"
        
        # Initialize Athena client
        self.athena_client = AthenaClient(
            database=database,
            region=region,
            output_location=output_location
        )
    
    def get_required_params(self) -> list[str]:
        """Get list of required parameters.
        
        Returns:
            List containing 'query_type'
        """
        return ["query_type"]
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate input parameters.
        
        Args:
            parameters: Input parameters containing query_type, parameters, and optional limit
            
        Raises:
            UserInputError: If parameters are invalid
        """
        # Validate required parameters
        self.validate_required_params(parameters)
        
        query_type = parameters.get("query_type")
        
        # Validate query_type
        if query_type not in QUERY_TEMPLATES and query_type != "custom":
            raise UserInputError(
                f"Invalid query_type: {query_type}",
                suggestion=f"Use one of: {', '.join(list(QUERY_TEMPLATES.keys()) + ['custom'])}"
            )
        
        # Validate custom query has sql parameter
        if query_type == "custom":
            if "sql" not in parameters.get("parameters", {}):
                raise UserInputError(
                    "Custom query requires 'sql' parameter",
                    suggestion="Provide SQL query in parameters.sql"
                )
        
        # Validate limit if provided
        limit = parameters.get("limit")
        if limit is not None:
            try:
                limit_int = int(limit)
                if limit_int <= 0:
                    raise UserInputError(
                        f"limit must be positive, got: {limit}",
                        suggestion="Provide a positive integer for limit"
                    )
                if limit_int > 1000:
                    raise UserInputError(
                        f"limit cannot exceed 1000, got: {limit}",
                        suggestion="Use a limit of 1000 or less, or implement pagination"
                    )
                parameters["limit"] = limit_int
            except (ValueError, TypeError):
                raise UserInputError(
                    f"limit must be an integer, got: {limit}",
                    suggestion="Provide a valid integer for limit"
                )
        
        # Validate page_size if provided
        page_size = parameters.get("page_size")
        if page_size is not None:
            try:
                page_size_int = int(page_size)
                if page_size_int <= 0:
                    raise UserInputError(
                        f"page_size must be positive, got: {page_size}",
                        suggestion="Provide a positive integer for page_size"
                    )
                if page_size_int > 100:
                    raise UserInputError(
                        f"page_size cannot exceed 100, got: {page_size}",
                        suggestion="Use a page_size of 100 or less"
                    )
                parameters["page_size"] = page_size_int
            except (ValueError, TypeError):
                raise UserInputError(
                    f"page_size must be an integer, got: {page_size}",
                    suggestion="Provide a valid integer for page_size"
                )
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Athena query.
        
        Args:
            parameters: Validated parameters with query_type, parameters, and optional limit
            
        Returns:
            Dictionary containing query results and metadata
            
        Raises:
            BackendServiceError: If query execution fails
        """
        import time
        
        query_type = parameters["query_type"]
        query_params = parameters.get("parameters", {})
        limit = parameters.get("limit", 10)
        page_size = parameters.get("page_size", 10)
        offset = parameters.get("offset", 0)
        
        try:
            # Build query
            if query_type == "custom":
                query = query_params["sql"]
            else:
                query = self._build_query_from_template(query_type, query_params)
            
            # Add pagination
            query = self._add_pagination(query, limit, offset)
            
            # Execute query and measure time
            start_time = time.time()
            results = self.athena_client.execute_query(query)
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Calculate pagination info
            total_results = len(results)
            has_more = total_results >= limit
            
            # Apply page_size for response
            paginated_results = results[:page_size]
            
            return {
                "results": paginated_results,
                "row_count": len(paginated_results),
                "total_count": total_results,
                "execution_time_ms": execution_time_ms,
                "query_type": query_type,
                "has_more": has_more,
                "next_offset": offset + page_size if has_more else None,
                "pagination": {
                    "page_size": page_size,
                    "offset": offset,
                    "limit": limit
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to execute Athena query: {str(e)}")
            
            # Parse Athena-specific errors
            error_message = str(e)
            if "SYNTAX_ERROR" in error_message:
                raise UserInputError(
                    f"SQL syntax error: {error_message}",
                    suggestion="Check your SQL query syntax"
                )
            elif "TABLE_NOT_FOUND" in error_message or "does not exist" in error_message:
                raise BackendServiceError(
                    f"Table not found: {error_message}",
                    suggestion="Verify that the required Glue tables have been created"
                )
            elif "COLUMN_NOT_FOUND" in error_message:
                raise UserInputError(
                    f"Column not found: {error_message}",
                    suggestion="Check that column names match the table schema"
                )
            else:
                raise BackendServiceError(
                    f"Query execution failed: {error_message}",
                    suggestion="Check CloudWatch logs for details or try again later"
                )
    
    def _build_query_from_template(
        self, 
        query_type: str, 
        params: Dict[str, Any]
    ) -> str:
        """Build SQL query from template.
        
        Args:
            query_type: Type of query template to use
            params: Parameters to substitute into template
            
        Returns:
            SQL query string
            
        Raises:
            UserInputError: If required parameters are missing
        """
        template = QUERY_TEMPLATES[query_type]
        
        # Validate required parameters for each query type
        required_params = self._get_required_params_for_query_type(query_type)
        missing_params = [p for p in required_params if p not in params]
        
        if missing_params:
            raise UserInputError(
                f"Missing required parameters for {query_type}: {', '.join(missing_params)}",
                suggestion=f"Provide values for: {', '.join(missing_params)}"
            )
        
        # Set defaults for optional parameters
        params = self._apply_defaults(query_type, params)
        
        try:
            # Substitute parameters into template
            query = template.format(**params)
            return query.strip()
        except KeyError as e:
            raise UserInputError(
                f"Missing parameter for query template: {str(e)}",
                suggestion=f"Provide the required parameter: {str(e)}"
            )
    
    def _get_required_params_for_query_type(self, query_type: str) -> List[str]:
        """Get required parameters for a query type.
        
        Args:
            query_type: Type of query
            
        Returns:
            List of required parameter names
        """
        requirements = {
            "brands_by_confidence": ["min_confidence", "max_confidence"],
            "brands_by_category": ["sector"],
            "recent_workflows": ["days"],
            "escalations_pending": [],
            "low_confidence_brands": ["threshold"],
            "brands_by_status": ["status"],
        }
        return requirements.get(query_type, [])
    
    def _apply_defaults(self, query_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values for optional parameters.
        
        Args:
            query_type: Type of query
            params: User-provided parameters
            
        Returns:
            Parameters with defaults applied
        """
        params = params.copy()
        
        # Apply defaults based on query type
        if query_type == "brands_by_confidence":
            params.setdefault("min_confidence", 0.0)
            params.setdefault("max_confidence", 1.0)
        elif query_type == "recent_workflows":
            params.setdefault("days", 7)
        elif query_type == "low_confidence_brands":
            params.setdefault("threshold", 0.7)
        
        return params
    
    def _add_pagination(self, query: str, limit: int, offset: int) -> str:
        """Add pagination to query.
        
        Args:
            query: SQL query
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            Query with LIMIT and OFFSET clauses
        """
        # Remove existing LIMIT clause if present
        query_upper = query.upper()
        if "LIMIT" in query_upper:
            query = query[:query_upper.index("LIMIT")].strip()
        
        # Add LIMIT and OFFSET
        query += f" LIMIT {limit}"
        if offset > 0:
            query += f" OFFSET {offset}"
        
        return query


# Lambda handler entry point
handler_instance = ExecuteAthenaQueryHandler()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point.
    
    Args:
        event: Lambda event with parameters
        context: Lambda context
        
    Returns:
        Standardized response dictionary
    """
    return handler_instance.handle(event, context)
