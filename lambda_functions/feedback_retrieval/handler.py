"""
Lambda function for feedback retrieval from Quick Suite interface.

This function retrieves feedback history for a brand to display in Quick Suite.
"""

import json
import os
import boto3
from typing import Dict, Any, List
from boto3.dynamodb.conditions import Key

# Initialize AWS clients
s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
S3_BUCKET = os.environ.get('S3_BUCKET', 'brand-generator-rwrd-023-eu-west-1')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'brand-metadata-state')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle feedback retrieval request from Quick Suite.
    
    Expected path parameters:
    - brandid: int
    
    Optional query parameters:
    - limit: int (default: 50)
    - include_metadata_history: bool (default: true)
    """
    try:
        # Extract brandid from path parameters
        path_parameters = event.get('pathParameters', {})
        brandid = path_parameters.get('brandid')
        
        if not brandid:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'brandid is required'})
            }
        
        try:
            brandid = int(brandid)
        except ValueError:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'brandid must be an integer'})
            }
        
        # Extract query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        limit = int(query_params.get('limit', 50))
        include_metadata_history = query_params.get('include_metadata_history', 'true').lower() == 'true'
        
        # Retrieve feedback history from DynamoDB
        feedback_history = get_feedback_history(brandid, limit)
        
        # Retrieve metadata version history if requested
        metadata_history = []
        if include_metadata_history:
            metadata_history = get_metadata_history(brandid)
        
        # Get current brand status
        brand_status = get_brand_status(brandid)
        
        # Calculate statistics
        stats = calculate_feedback_stats(feedback_history)
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'brandid': brandid,
                'feedback_history': feedback_history,
                'metadata_history': metadata_history,
                'brand_status': brand_status,
                'statistics': stats
            })
        }
    
    except Exception as e:
        print(f"Error retrieving feedback: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }


def get_feedback_history(brandid: int, limit: int) -> List[Dict[str, Any]]:
    """Retrieve feedback history for a brand from DynamoDB."""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        response = table.query(
            KeyConditionExpression=Key('pk').eq(f"BRAND#{brandid}") & Key('sk').begins_with('FEEDBACK#'),
            ScanIndexForward=False,  # Sort descending (newest first)
            Limit=limit
        )
        
        feedback_items = []
        for item in response.get('Items', []):
            feedback_items.append({
                'timestamp': item.get('timestamp'),
                'feedback_type': item.get('feedback_type'),
                'feedback_text': item.get('feedback_text'),
                'misclassified_combos': item.get('misclassified_combos', []),
                'metadata_version': item.get('metadata_version'),
                'processing_result': item.get('processing_result', {})
            })
        
        return feedback_items
    
    except Exception as e:
        print(f"Error retrieving feedback history: {str(e)}")
        return []


def get_metadata_history(brandid: int) -> List[Dict[str, Any]]:
    """Retrieve metadata version history for a brand from S3."""
    try:
        # List all metadata versions for the brand
        prefix = f"metadata/brand_{brandid}_v"
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=prefix
        )
        
        metadata_versions = []
        for obj in response.get('Contents', []):
            # Extract version number from key
            key = obj['Key']
            try:
                version = int(key.split('_v')[1].split('.')[0])
            except (IndexError, ValueError):
                continue
            
            # Retrieve metadata
            metadata_response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            metadata = json.loads(metadata_response['Body'].read().decode('utf-8'))
            
            metadata_versions.append({
                'version': version,
                'timestamp': obj['LastModified'].isoformat(),
                'regex_pattern': metadata.get('metadata', {}).get('regex_pattern'),
                'mccids': metadata.get('metadata', {}).get('mccids', []),
                'confidence_score': metadata.get('metadata', {}).get('confidence_score'),
                'iterations': metadata.get('metadata', {}).get('generation_metadata', {}).get('iterations')
            })
        
        # Sort by version descending
        metadata_versions.sort(key=lambda x: x['version'], reverse=True)
        
        return metadata_versions
    
    except Exception as e:
        print(f"Error retrieving metadata history: {str(e)}")
        return []


def get_brand_status(brandid: int) -> Dict[str, Any]:
    """Retrieve current brand status from DynamoDB."""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        response = table.get_item(
            Key={
                'pk': f"BRAND#{brandid}",
                'sk': 'STATUS'
            }
        )
        
        item = response.get('Item', {})
        
        return {
            'status': item.get('status', 'pending'),
            'metadata_version': item.get('metadata_version', 1),
            'approved_at': item.get('approved_at'),
            'last_updated': item.get('timestamp')
        }
    
    except Exception as e:
        print(f"Error retrieving brand status: {str(e)}")
        return {
            'status': 'unknown',
            'metadata_version': 1
        }


def calculate_feedback_stats(feedback_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate statistics from feedback history."""
    if not feedback_history:
        return {
            'total_feedback_count': 0,
            'approval_count': 0,
            'rejection_count': 0,
            'general_feedback_count': 0,
            'specific_examples_count': 0,
            'iteration_count': 0
        }
    
    stats = {
        'total_feedback_count': len(feedback_history),
        'approval_count': 0,
        'rejection_count': 0,
        'general_feedback_count': 0,
        'specific_examples_count': 0,
        'iteration_count': 0
    }
    
    for feedback in feedback_history:
        feedback_type = feedback.get('feedback_type', '')
        
        if feedback_type == 'approve':
            stats['approval_count'] += 1
        elif feedback_type == 'reject':
            stats['rejection_count'] += 1
        elif feedback_type == 'general':
            stats['general_feedback_count'] += 1
        elif feedback_type == 'specific_examples':
            stats['specific_examples_count'] += 1
    
    # Calculate iteration count (rejections + general feedback + specific examples)
    stats['iteration_count'] = (
        stats['rejection_count'] + 
        stats['general_feedback_count'] + 
        stats['specific_examples_count']
    )
    
    return stats

