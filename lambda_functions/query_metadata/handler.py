"""Lambda function for querying brand metadata.

This tool retrieves brand metadata from S3 for the Conversational Interface Agent.
Supports retrieving specific versions or the latest version of metadata.
"""

import sys
import os
from typing import Any, Dict

# Add shared directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.storage.s3_client import S3Client
from shared.utils.base_handler import BaseToolHandler
from shared.utils.error_handler import UserInputError, BackendServiceError


class QueryMetadataHandler(BaseToolHandler):
    """Handler for querying brand metadata from S3."""
    
    def __init__(self):
        """Initialize handler with S3 client."""
        super().__init__("query_metadata")
        
        # Get configuration from environment
        bucket = os.environ.get("S3_BUCKET", "brand-generator-rwrd-023-eu-west-1")
        region = os.environ.get("AWS_REGION", "eu-west-1")
        
        # Initialize S3 client
        self.s3_client = S3Client(bucket=bucket, region=region)
    
    def get_required_params(self) -> list[str]:
        """Get list of required parameters.
        
        Returns:
            List containing 'brandid'
        """
        return ["brandid"]
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate input parameters.
        
        Args:
            parameters: Input parameters containing brandid and optional version
            
        Raises:
            UserInputError: If parameters are invalid
        """
        # Validate required parameters
        self.validate_required_params(parameters)
        
        # Validate brandid is an integer
        brandid = parameters.get("brandid")
        if not isinstance(brandid, int):
            try:
                parameters["brandid"] = int(brandid)
            except (ValueError, TypeError):
                raise UserInputError(
                    f"brandid must be an integer, got: {brandid}",
                    suggestion="Provide a valid brand ID as an integer"
                )
        
        # Validate brandid is positive
        if parameters["brandid"] <= 0:
            raise UserInputError(
                f"brandid must be positive, got: {parameters['brandid']}",
                suggestion="Provide a valid positive brand ID"
            )
        
        # Validate version if provided
        version = parameters.get("version")
        if version is not None:
            if version != "latest":
                try:
                    version_int = int(version)
                    if version_int <= 0:
                        raise UserInputError(
                            f"version must be positive or 'latest', got: {version}",
                            suggestion="Provide a valid version number or 'latest'"
                        )
                    parameters["version"] = version_int
                except (ValueError, TypeError):
                    raise UserInputError(
                        f"version must be an integer or 'latest', got: {version}",
                        suggestion="Provide a valid version number or 'latest'"
                    )
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute metadata retrieval.
        
        Args:
            parameters: Validated parameters with brandid and optional version
            
        Returns:
            Dictionary containing metadata or error information
            
        Raises:
            BackendServiceError: If S3 retrieval fails
        """
        brandid = parameters["brandid"]
        version = parameters.get("version", "latest")
        
        try:
            # Determine S3 key based on version
            if version == "latest":
                # Try to read metadata without version suffix (latest)
                metadata = self.s3_client.read_metadata(brandid, prefix="metadata")
                
                if metadata is None:
                    # Try with version suffix pattern
                    metadata = self._find_latest_version(brandid)
            else:
                # Read specific version
                key = f"metadata/brand_{brandid}_v{version}.json"
                metadata = self.s3_client.read_json(key)
            
            # Check if metadata was found
            if metadata is None:
                return {
                    "found": False,
                    "brandid": brandid,
                    "version": version,
                    "message": f"No metadata found for brand {brandid}" + 
                              (f" version {version}" if version != "latest" else "")
                }
            
            # Format metadata for presentation
            formatted_metadata = self._format_metadata(metadata, brandid, version)
            
            return {
                "found": True,
                "brandid": brandid,
                "metadata": formatted_metadata
            }
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve metadata for brand {brandid}: {str(e)}")
            raise BackendServiceError(
                f"Failed to retrieve metadata from S3: {str(e)}",
                suggestion="Check that the S3 bucket is accessible and the brand ID is correct"
            )
    
    def _find_latest_version(self, brandid: int) -> Dict[str, Any]:
        """Find the latest version of metadata for a brand.
        
        Args:
            brandid: Brand ID
            
        Returns:
            Latest metadata dictionary or None if not found
        """
        try:
            # List all keys for this brand
            prefix = f"metadata/brand_{brandid}"
            keys = self.s3_client.list_keys(prefix)
            
            if not keys:
                return None
            
            # Filter for versioned files and extract version numbers
            versioned_keys = []
            for key in keys:
                if "_v" in key and key.endswith(".json"):
                    try:
                        # Extract version number from key like "brand_123_v5.json"
                        version_str = key.split("_v")[1].replace(".json", "")
                        version_num = int(version_str)
                        versioned_keys.append((version_num, key))
                    except (ValueError, IndexError):
                        continue
            
            if not versioned_keys:
                return None
            
            # Sort by version number and get the latest
            versioned_keys.sort(reverse=True)
            latest_key = versioned_keys[0][1]
            
            # Read the latest version
            return self.s3_client.read_json(latest_key)
            
        except Exception as e:
            self.logger.warning(f"Error finding latest version for brand {brandid}: {str(e)}")
            return None
    
    def _format_metadata(
        self, 
        metadata: Dict[str, Any], 
        brandid: int, 
        version: Any
    ) -> Dict[str, Any]:
        """Format metadata for readable presentation.
        
        Args:
            metadata: Raw metadata dictionary
            brandid: Brand ID
            version: Version requested
            
        Returns:
            Formatted metadata dictionary
        """
        # Extract key fields with defaults
        formatted = {
            "brandid": brandid,
            "brandname": metadata.get("brandname", "Unknown"),
            "regex": metadata.get("regex", ""),
            "mccids": metadata.get("mccids", []),
            "confidence_score": metadata.get("confidence_score", 0.0),
            "version": metadata.get("version", version if version != "latest" else 1),
            "generated_at": metadata.get("generated_at", "Unknown"),
        }
        
        # Add optional fields if present
        if "evaluator_issues" in metadata:
            formatted["evaluator_issues"] = metadata["evaluator_issues"]
        
        if "coverage_narratives_matched" in metadata:
            formatted["coverage_narratives_matched"] = metadata["coverage_narratives_matched"]
        
        if "coverage_false_positives" in metadata:
            formatted["coverage_false_positives"] = metadata["coverage_false_positives"]
        
        if "matched_combos" in metadata:
            matched_combos = metadata["matched_combos"]
            formatted["matched_combos_summary"] = {
                "confirmed_count": len(matched_combos.get("confirmed", [])),
                "excluded_count": len(matched_combos.get("excluded", [])),
                "requires_review_count": len(matched_combos.get("requires_human_review", []))
            }
        
        # Add sector if present
        if "sector" in metadata:
            formatted["sector"] = metadata["sector"]
        
        return formatted


# Lambda handler entry point
handler_instance = QueryMetadataHandler()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point.
    
    Args:
        event: Lambda event with parameters
        context: Lambda context
        
    Returns:
        Standardized response dictionary
    """
    return handler_instance.handle(event, context)
