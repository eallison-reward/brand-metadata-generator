"""
Lambda function to update monitoring metrics and CloudWatch.

This function pushes metrics to CloudWatch for monitoring and alerting.
"""

import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any

# Initialize AWS clients
cloudwatch = boto3.client('cloudwatch', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
NAMESPACE = f"BrandMetadataGenerator/{ENVIRONMENT}"


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Update monitoring metrics.
    
    Input:
    {
        "summary": {
            "total_brands_processed": int,
            "succeeded_brands": int,
            "failed_brands": int,
            "brands_requiring_review": int,
            "feedback_iterations": int,
            ...
        },
        "workflow_config": {...}
    }
    
    Output:
    {
        "status": "success",
        "metrics_published": int
    }
    """
    try:
        summary = event.get('summary', {})
        workflow_config = event.get('workflow_config', {})
        
        # Publish metrics to CloudWatch
        metrics_published = publish_metrics(summary)
        
        return {
            'statusCode': 200,
            'status': 'success',
            'metrics_published': metrics_published
        }
    
    except Exception as e:
        print(f"Error updating monitoring: {str(e)}")
        return {
            'statusCode': 500,
            'status': 'error',
            'error': str(e)
        }


def publish_metrics(summary: Dict[str, Any]) -> int:
    """Publish metrics to CloudWatch."""
    try:
        timestamp = datetime.utcnow()
        
        metrics = []
        
        # Total brands processed
        if 'total_brands_processed' in summary:
            metrics.append({
                'MetricName': 'TotalBrandsProcessed',
                'Value': summary['total_brands_processed'],
                'Unit': 'Count',
                'Timestamp': timestamp
            })
        
        # Succeeded brands
        if 'succeeded_brands' in summary:
            metrics.append({
                'MetricName': 'SucceededBrands',
                'Value': summary['succeeded_brands'],
                'Unit': 'Count',
                'Timestamp': timestamp
            })
        
        # Failed brands
        if 'failed_brands' in summary:
            metrics.append({
                'MetricName': 'FailedBrands',
                'Value': summary['failed_brands'],
                'Unit': 'Count',
                'Timestamp': timestamp
            })
        
        # Brands requiring review
        if 'brands_requiring_review' in summary:
            metrics.append({
                'MetricName': 'BrandsRequiringReview',
                'Value': summary['brands_requiring_review'],
                'Unit': 'Count',
                'Timestamp': timestamp
            })
        
        # Success rate
        if 'success_rate_percent' in summary:
            metrics.append({
                'MetricName': 'SuccessRate',
                'Value': summary['success_rate_percent'],
                'Unit': 'Percent',
                'Timestamp': timestamp
            })
        
        # Feedback iterations
        if 'feedback_iterations' in summary:
            metrics.append({
                'MetricName': 'FeedbackIterations',
                'Value': summary['feedback_iterations'],
                'Unit': 'Count',
                'Timestamp': timestamp
            })
        
        # Average iterations per brand
        if 'average_iterations_per_brand' in summary:
            metrics.append({
                'MetricName': 'AverageIterationsPerBrand',
                'Value': summary['average_iterations_per_brand'],
                'Unit': 'Count',
                'Timestamp': timestamp
            })
        
        # Combos matched
        if 'total_combos_matched' in summary:
            metrics.append({
                'MetricName': 'TotalCombosMatched',
                'Value': summary['total_combos_matched'],
                'Unit': 'Count',
                'Timestamp': timestamp
            })
        
        # Combos confirmed
        if 'total_combos_confirmed' in summary:
            metrics.append({
                'MetricName': 'TotalCombosConfirmed',
                'Value': summary['total_combos_confirmed'],
                'Unit': 'Count',
                'Timestamp': timestamp
            })
        
        # Combos excluded
        if 'total_combos_excluded' in summary:
            metrics.append({
                'MetricName': 'TotalCombosExcluded',
                'Value': summary['total_combos_excluded'],
                'Unit': 'Count',
                'Timestamp': timestamp
            })
        
        # Exclusion rate
        if 'exclusion_rate_percent' in summary:
            metrics.append({
                'MetricName': 'ExclusionRate',
                'Value': summary['exclusion_rate_percent'],
                'Unit': 'Percent',
                'Timestamp': timestamp
            })
        
        # Publish metrics in batches of 20 (CloudWatch limit)
        metrics_published = 0
        for i in range(0, len(metrics), 20):
            batch = metrics[i:i+20]
            cloudwatch.put_metric_data(
                Namespace=NAMESPACE,
                MetricData=batch
            )
            metrics_published += len(batch)
        
        return metrics_published
    
    except Exception as e:
        print(f"Error publishing metrics: {str(e)}")
        return 0

