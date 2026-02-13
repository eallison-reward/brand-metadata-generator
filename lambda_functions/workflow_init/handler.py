"""
Lambda function to initialize Brand Metadata Generator workflow.

This function validates inputs, loads configuration, and prepares
the workflow for execution.
"""

import json
import os
from typing import Dict, Any


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Initialize workflow configuration and validate inputs.
    
    Args:
        event: Input event containing workflow parameters
        context: Lambda context object
        
    Returns:
        Dictionary with workflow configuration
    """
    try:
        # Extract configuration from event or use defaults
        config = event.get("config", {})
        
        # Default configuration values
        default_config = {
            "confidence_threshold": 0.75,
            "max_iterations": 5,
            "batch_size": 10,
            "enable_confirmation": True,
            "enable_tiebreaker": True,
            "aws_region": os.environ.get("AWS_REGION", "eu-west-1"),
            "s3_bucket": os.environ.get("S3_BUCKET", "brand-generator-rwrd-023-eu-west-1"),
            "athena_database": os.environ.get("ATHENA_DATABASE", "brand_metadata_generator_db")
        }
        
        # Merge with provided config
        workflow_config = {**default_config, **config}
        
        # Validate configuration
        if not 0.0 <= workflow_config["confidence_threshold"] <= 1.0:
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")
        
        if workflow_config["max_iterations"] < 1:
            raise ValueError("max_iterations must be at least 1")
        
        if workflow_config["batch_size"] < 1:
            raise ValueError("batch_size must be at least 1")
        
        # Prepare workflow state
        workflow_state = {
            "workflow_id": context.request_id,
            "start_time": context.get_remaining_time_in_millis(),
            "status": "initialized",
            "brands_processed": 0,
            "brands_total": 0
        }
        
        return {
            "statusCode": 200,
            "config": workflow_config,
            "state": workflow_state,
            "message": "Workflow initialized successfully"
        }
        
    except ValueError as e:
        return {
            "statusCode": 400,
            "error": "ValidationError",
            "message": str(e)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "error": "InitializationError",
            "message": f"Failed to initialize workflow: {str(e)}"
        }
