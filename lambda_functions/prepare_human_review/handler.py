"""
Lambda function to prepare brands for human review in Quick Suite.

This function prepares brand data and creates review URLs for Quick Suite interface.
"""

import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any, List

# Initialize AWS clients
s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
S3_BUCKET = os.environ.get('S3_BUCKET', 'brand-generator-rwrd-023-eu-west-1')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'brand-metadata-state')
QUICK_SUITE_BASE_URL = os.environ.get('QUICK_SUITE_BASE_URL', 'https://bedrock.console.aws.amazon.com/quick-suite')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Prepare brands for human review.
    
    Input:
    {
        "brands_requiring_review": [int],
        "workflow_config": {...}
    }
    
    Output:
    {
        "review_url": str,
        "brands": [{"brandid": int, "brandname": str, ...}],
        "prepared_at": str
    }
    """
    try:
        brands_requiring_review = event.get('brands_requiring_review', [])
        workflow_config = event.get('workflow_config', {})
        
        if not brands_requiring_review:
            return {
                'statusCode': 200,
                'review_url': None,
                'brands': [],
                'prepared_at': get_current_timestamp()
            }
        
        # Prepare brand data for review
        brands_data = []
        for brandid in brands_requiring_review:
            brand_data = prepare_brand_for_review(brandid)
            if brand_data:
                brands_data.append(brand_data)
        
        # Update brand status to "awaiting_review"
        for brandid in brands_requiring_review:
            update_brand_status(brandid, 'awaiting_review')
        
        # Generate Quick Suite review URL
        review_url = generate_review_url(brands_requiring_review)
        
        return {
            'statusCode': 200,
            'review_url': review_url,
            'brands': brands_data,
            'prepared_at': get_current_timestamp()
        }
    
    except Exception as e:
        print(f"Error preparing human review: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e)
        }


def prepare_brand_for_review(brandid: int) -> Dict[str, Any]:
    """Prepare brand data for human review."""
    try:
        # Retrieve brand metadata from S3
        s3_key = f"metadata/brand_{brandid}.json"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        metadata = json.loads(response['Body'].read().decode('utf-8'))
        
        return {
            'brandid': brandid,
            'brandname': metadata.get('brandname', f'Brand {brandid}'),
            'sector': metadata.get('sector', 'Unknown'),
            'regex_pattern': metadata.get('metadata', {}).get('regex_pattern'),
            'mccids': metadata.get('metadata', {}).get('mccids', []),
            'confidence_score': metadata.get('metadata', {}).get('confidence_score'),
            'matched_combos_count': len(metadata.get('matched_combos', {}).get('confirmed', [])),
            'excluded_combos_count': len(metadata.get('matched_combos', {}).get('excluded', [])),
            'requires_review_reason': metadata.get('metadata', {}).get('generation_metadata', {}).get('issues_identified', [])
        }
    
    except Exception as e:
        print(f"Error preparing brand {brandid}: {str(e)}")
        return None


def update_brand_status(brandid: int, status: str) -> None:
    """Update brand status in DynamoDB."""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        table.put_item(
            Item={
                'pk': f"BRAND#{brandid}",
                'sk': 'STATUS',
                'brandid': brandid,
                'status': status,
                'timestamp': get_current_timestamp(),
                'ttl': int(datetime.utcnow().timestamp()) + (365 * 24 * 60 * 60)  # 1 year
            }
        )
    except Exception as e:
        print(f"Error updating brand status: {str(e)}")


def generate_review_url(brandids: List[int]) -> str:
    """Generate Quick Suite review URL."""
    # Generate URL for Quick Suite interface
    brand_ids_param = ','.join(str(bid) for bid in brandids)
    return f"{QUICK_SUITE_BASE_URL}/review?brands={brand_ids_param}&environment={ENVIRONMENT}"


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().isoformat() + "Z"

