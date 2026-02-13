"""Athena client for querying brand metadata database."""

import time
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError


class AthenaClient:
    """Client for executing Athena queries against brand_metadata_generator_db."""

    def __init__(
        self,
        database: str = "brand_metadata_generator_db",
        region: str = "eu-west-1",
        output_location: str = "s3://brand-generator-rwrd-023-eu-west-1/query-results/",
        max_retries: int = 3,
    ):
        """Initialize Athena client.
        
        Args:
            database: Athena database name
            region: AWS region
            output_location: S3 location for query results
            max_retries: Maximum number of retry attempts
        """
        self.database = database
        self.region = region
        self.output_location = output_location
        self.max_retries = max_retries
        self.client = boto3.client("athena", region_name=region)

    def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute Athena query and return results.
        
        Args:
            query: SQL query to execute
            parameters: Optional query parameters for parameterized queries
            
        Returns:
            List of result rows as dictionaries
            
        Raises:
            Exception: If query execution fails after retries
        """
        for attempt in range(self.max_retries):
            try:
                # Start query execution
                execution_id = self._start_query_execution(query)
                
                # Wait for query to complete
                self._wait_for_query_completion(execution_id)
                
                # Get and return results
                return self._get_query_results(execution_id)
                
            except ClientError as e:
                if attempt == self.max_retries - 1:
                    raise Exception(f"Query execution failed after {self.max_retries} attempts: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
                
        return []

    def _start_query_execution(self, query: str) -> str:
        """Start Athena query execution.
        
        Args:
            query: SQL query to execute
            
        Returns:
            Query execution ID
        """
        response = self.client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": self.database},
            ResultConfiguration={"OutputLocation": self.output_location},
        )
        return response["QueryExecutionId"]

    def _wait_for_query_completion(
        self, execution_id: str, poll_interval: int = 1, timeout: int = 300
    ) -> None:
        """Wait for query to complete.
        
        Args:
            execution_id: Query execution ID
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait
            
        Raises:
            Exception: If query fails or times out
        """
        elapsed = 0
        while elapsed < timeout:
            response = self.client.get_query_execution(QueryExecutionId=execution_id)
            status = response["QueryExecution"]["Status"]["State"]
            
            if status == "SUCCEEDED":
                return
            elif status in ["FAILED", "CANCELLED"]:
                reason = response["QueryExecution"]["Status"].get(
                    "StateChangeReason", "Unknown error"
                )
                raise Exception(f"Query {status.lower()}: {reason}")
            
            time.sleep(poll_interval)
            elapsed += poll_interval
            
        raise Exception(f"Query timed out after {timeout} seconds")

    def _get_query_results(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get query results.
        
        Args:
            execution_id: Query execution ID
            
        Returns:
            List of result rows as dictionaries
        """
        results = []
        paginator = self.client.get_paginator("get_query_results")
        
        for page in paginator.paginate(QueryExecutionId=execution_id):
            rows = page["ResultSet"]["Rows"]
            
            # First row contains column names
            if not results and rows:
                columns = [col["VarCharValue"] for col in rows[0]["Data"]]
                rows = rows[1:]  # Skip header row
            else:
                columns = [col["VarCharValue"] for col in page["ResultSet"]["Rows"][0]["Data"]]
            
            # Convert rows to dictionaries
            for row in rows:
                row_dict = {}
                for i, col in enumerate(row.get("Data", [])):
                    value = col.get("VarCharValue")
                    # Convert to appropriate type
                    if value is not None:
                        row_dict[columns[i]] = self._convert_value(value)
                    else:
                        row_dict[columns[i]] = None
                results.append(row_dict)
                
        return results

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate Python type.
        
        Args:
            value: String value from Athena
            
        Returns:
            Converted value (int, float, or str)
        """
        # Try int
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value

    def query_table(
        self, table_name: str, columns: str = "*", where: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Query a table with optional filters.
        
        Args:
            table_name: Name of table to query
            columns: Columns to select (default: *)
            where: Optional WHERE clause (without WHERE keyword)
            limit: Optional LIMIT value
            
        Returns:
            List of result rows
        """
        query = f"SELECT {columns} FROM {table_name}"
        
        if where:
            query += f" WHERE {where}"
            
        if limit:
            query += f" LIMIT {limit}"
            
        return self.execute_query(query)

    def get_table_count(self, table_name: str, where: Optional[str] = None) -> int:
        """Get row count for a table.
        
        Args:
            table_name: Name of table
            where: Optional WHERE clause
            
        Returns:
            Number of rows
        """
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        
        if where:
            query += f" WHERE {where}"
            
        results = self.execute_query(query)
        return results[0]["count"] if results else 0
