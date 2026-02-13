"""S3 client for storing and retrieving brand metadata."""

import json
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError


class S3Client:
    """Client for S3 operations on brand metadata bucket."""

    def __init__(
        self,
        bucket: str = "brand-generator-rwrd-023-eu-west-1",
        region: str = "eu-west-1",
    ):
        """Initialize S3 client.
        
        Args:
            bucket: S3 bucket name
            region: AWS region
        """
        self.bucket = bucket
        self.region = region
        self.client = boto3.client("s3", region_name=region)

    def write_metadata(
        self, brandid: int, metadata: Dict[str, Any], prefix: str = "metadata"
    ) -> str:
        """Write brand metadata to S3.
        
        Args:
            brandid: Brand ID
            metadata: Metadata dictionary to store
            prefix: S3 key prefix (default: metadata)
            
        Returns:
            S3 key where metadata was stored
            
        Raises:
            Exception: If write fails
        """
        key = f"{prefix}/brand_{brandid}.json"
        
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=json.dumps(metadata, indent=2),
                ContentType="application/json",
            )
            return key
        except ClientError as e:
            raise Exception(f"Failed to write metadata to S3: {e}")

    def read_metadata(
        self, brandid: int, prefix: str = "metadata"
    ) -> Optional[Dict[str, Any]]:
        """Read brand metadata from S3.
        
        Args:
            brandid: Brand ID
            prefix: S3 key prefix (default: metadata)
            
        Returns:
            Metadata dictionary or None if not found
        """
        key = f"{prefix}/brand_{brandid}.json"
        
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            return json.loads(content)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise Exception(f"Failed to read metadata from S3: {e}")

    def write_json(self, key: str, data: Dict[str, Any]) -> str:
        """Write JSON data to S3.
        
        Args:
            key: S3 key
            data: Data dictionary to store
            
        Returns:
            S3 key where data was stored
        """
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=json.dumps(data, indent=2),
                ContentType="application/json",
            )
            return key
        except ClientError as e:
            raise Exception(f"Failed to write to S3: {e}")

    def read_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Read JSON data from S3.
        
        Args:
            key: S3 key
            
        Returns:
            Data dictionary or None if not found
        """
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            return json.loads(content)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise Exception(f"Failed to read from S3: {e}")

    def list_keys(self, prefix: str) -> list[str]:
        """List all keys with given prefix.
        
        Args:
            prefix: S3 key prefix
            
        Returns:
            List of S3 keys
        """
        keys = []
        paginator = self.client.get_paginator("list_objects_v2")
        
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            if "Contents" in page:
                keys.extend([obj["Key"] for obj in page["Contents"]])
                
        return keys

    def delete_key(self, key: str) -> None:
        """Delete object from S3.
        
        Args:
            key: S3 key to delete
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            raise Exception(f"Failed to delete from S3: {e}")

    def key_exists(self, key: str) -> bool:
        """Check if key exists in S3.
        
        Args:
            key: S3 key to check
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise Exception(f"Failed to check S3 key: {e}")
