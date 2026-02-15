"""DynamoDB client for brand processing status tracking."""

from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError


class DynamoDBClient:
    """Client for DynamoDB operations on brand processing status."""

    def __init__(
        self,
        table_name: str = "brand_processing_status_dev",
        region: str = "eu-west-1",
    ):
        """Initialize DynamoDB client.
        
        Args:
            table_name: DynamoDB table name
            region: AWS region
        """
        self.table_name = table_name
        self.region = region
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.table = self.dynamodb.Table(table_name)

    def query_brands_by_status(
        self, status: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Query brands by status using GSI.
        
        Args:
            status: Status to filter by (optional)
            limit: Maximum number of results
            
        Returns:
            List of brand records
        """
        try:
            if status:
                # Query using status GSI
                response = self.table.query(
                    IndexName="status-index",
                    KeyConditionExpression="status = :status",
                    ExpressionAttributeValues={":status": status},
                    Limit=limit,
                )
            else:
                # Scan all records (limited)
                response = self.table.scan(Limit=limit)
            
            return response.get("Items", [])
            
        except ClientError as e:
            raise Exception(f"Failed to query brands by status: {e}")

    def get_brand_by_id(self, brandid: int) -> Optional[Dict[str, Any]]:
        """Get a single brand by ID.
        
        Args:
            brandid: Brand ID
            
        Returns:
            Brand record or None if not found
        """
        try:
            response = self.table.get_item(Key={"brandid": brandid})
            return response.get("Item")
            
        except ClientError as e:
            raise Exception(f"Failed to get brand {brandid}: {e}")

    def put_brand(self, brand_data: Dict[str, Any]) -> None:
        """Insert or update a brand record.
        
        Args:
            brand_data: Brand data dictionary
        """
        try:
            self.table.put_item(Item=brand_data)
            
        except ClientError as e:
            raise Exception(f"Failed to put brand: {e}")

    def update_brand_status(
        self, brandid: int, status: str, **additional_fields
    ) -> None:
        """Update brand status and other fields.
        
        Args:
            brandid: Brand ID
            status: New status
            **additional_fields: Additional fields to update
        """
        try:
            # Build update expression
            update_expression = "SET #status = :status, updated_at = :updated_at"
            expression_attribute_names = {"#status": "status"}
            expression_attribute_values = {
                ":status": status,
                ":updated_at": self._get_current_timestamp(),
            }
            
            # Add additional fields
            for field, value in additional_fields.items():
                update_expression += f", {field} = :{field}"
                expression_attribute_values[f":{field}"] = value
            
            self.table.update_item(
                Key={"brandid": brandid},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
            )
            
        except ClientError as e:
            raise Exception(f"Failed to update brand {brandid} status: {e}")

    def get_status_counts(self) -> Dict[str, int]:
        """Get count of brands by status.
        
        Returns:
            Dictionary mapping status to count
        """
        try:
            # Scan table and count by status
            response = self.table.scan(
                ProjectionExpression="status"
            )
            
            status_counts = {}
            for item in response.get("Items", []):
                status = item.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Handle pagination if needed
            while "LastEvaluatedKey" in response:
                response = self.table.scan(
                    ProjectionExpression="status",
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                for item in response.get("Items", []):
                    status = item.get("status", "unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1
            
            return status_counts
            
        except ClientError as e:
            raise Exception(f"Failed to get status counts: {e}")

    def batch_put_brands(self, brands: List[Dict[str, Any]]) -> None:
        """Batch insert multiple brand records.
        
        Args:
            brands: List of brand data dictionaries
        """
        try:
            # DynamoDB batch_writer handles batching automatically
            with self.table.batch_writer() as batch:
                for brand in brands:
                    batch.put_item(Item=brand)
                    
        except ClientError as e:
            raise Exception(f"Failed to batch put brands: {e}")

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format.
        
        Returns:
            ISO formatted timestamp string
        """
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()