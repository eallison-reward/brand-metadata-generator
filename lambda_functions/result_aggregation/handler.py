"""
Lambda function to aggregate workflow results.

This function collects and summarizes results from all processed brands,
generating final statistics and reports.
"""

import json
import os
import boto3
from typing import Dict, Any, List
from datetime import datetime


# Initialize AWS clients
s3_client = boto3.client('s3', region_name=os.environ.get("AWS_REGION", "eu-west-1"))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Aggregate results from all processed brands.
    
    Args:
        event: Input event containing orchestrator results
        context: Lambda context object
        
    Returns:
        Dictionary with aggregated statistics and summary
    """
    try:
        # Extract orchestrator results
        orchestrator_result = event.get("orchestrator_result", {})
        workflow_config = event.get("workflow_config", {})
        
        # Get S3 bucket from environment
        s3_bucket = os.environ.get("S3_BUCKET", "brand-generator-rwrd-023-eu-west-1")
        
        # Extract brand lists
        succeeded_brands = orchestrator_result.get("succeeded_brands", [])
        failed_brands = orchestrator_result.get("failed_brands", [])
        brands_requiring_review = orchestrator_result.get("brands_requiring_review", [])
        
        # Aggregate statistics
        total_brands = len(succeeded_brands) + len(failed_brands)
        success_rate = (len(succeeded_brands) / total_brands * 100) if total_brands > 0 else 0
        
        # Collect detailed statistics from S3 metadata files
        total_combos_matched = 0
        total_combos_confirmed = 0
        total_combos_excluded = 0
        total_ties_resolved = 0
        
        for brand_id in succeeded_brands:
            try:
                # Read brand metadata from S3
                metadata_key = f"metadata/brand_{brand_id}.json"
                response = s3_client.get_object(Bucket=s3_bucket, Key=metadata_key)
                metadata = json.loads(response['Body'].read().decode('utf-8'))
                
                # Aggregate statistics
                stats = metadata.get("statistics", {})
                total_combos_matched += stats.get("total_matched", 0)
                total_combos_confirmed += stats.get("confirmed", 0)
                total_combos_excluded += stats.get("excluded", 0)
                total_ties_resolved += stats.get("ties_resolved", 0)
                
            except Exception as e:
                # Log error but continue aggregation
                print(f"Warning: Could not read metadata for brand {brand_id}: {str(e)}")
                continue
        
        # Create summary report
        summary = {
            "workflow_id": workflow_config.get("state", {}).get("workflow_id"),
            "execution_time": datetime.utcnow().isoformat(),
            "total_brands_processed": total_brands,
            "succeeded_brands": len(succeeded_brands),
            "failed_brands": len(failed_brands),
            "brands_requiring_review": len(brands_requiring_review),
            "success_rate_percent": round(success_rate, 2),
            "total_combos_matched": total_combos_matched,
            "total_combos_confirmed": total_combos_confirmed,
            "total_combos_excluded": total_combos_excluded,
            "total_ties_resolved": total_ties_resolved,
            "confirmation_rate_percent": round(
                (total_combos_confirmed / total_combos_matched * 100) if total_combos_matched > 0 else 0,
                2
            ),
            "exclusion_rate_percent": round(
                (total_combos_excluded / total_combos_matched * 100) if total_combos_matched > 0 else 0,
                2
            )
        }
        
        # Store summary report in S3
        summary_key = f"reports/workflow_{workflow_config.get('state', {}).get('workflow_id')}_summary.json"
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=summary_key,
            Body=json.dumps(summary, indent=2),
            ContentType='application/json'
        )
        
        return {
            "statusCode": 200,
            "summary": summary,
            "succeeded_brands": succeeded_brands,
            "failed_brands": failed_brands,
            "brands_requiring_review": brands_requiring_review,
            "report_location": f"s3://{s3_bucket}/{summary_key}",
            "message": "Results aggregated successfully"
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "error": "AggregationError",
            "message": f"Failed to aggregate results: {str(e)}"
        }
