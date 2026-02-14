"""
Lambda function for brand data retrieval for Quick Suite interface.

This function retrieves complete brand data including metadata, matched combos,
and statistics for display in Quick Suite.
"""

import json
import os
import boto3
from typing import Dict, Any

# Initialize AWS clients
s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
athena_client = boto3.client('athena', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
S3_BUCKET = os.environ.get('S3_BUCKET', 'brand-generator-rwrd-023-eu-west-1')
ATHENA_DATABASE = os.environ.get('ATHENA_DATABASE', 'brand_metadata_generator_db')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle brand data retrieval request from Quick Suite.
    
    Expected path parameters:
    - brandid: int
    
    Optional query parameters:
    - include_combos: bool (default: true)
    - include_narratives: bool (default: true)
    - sample_size: int (default: 10) - number of sample narratives to return
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
        include_combos = query_params.get('include_combos', 'true').lower() == 'true'
        include_narratives = query_params.get('include_narratives', 'true').lower() == 'true'
        sample_size = int(query_params.get('sample_size', 10))
        
        # Retrieve brand metadata from S3
        brand_data = get_brand_metadata(brandid)
        
        if not brand_data:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'Brand {brandid} not found'})
            }
        
        # Add combo details if requested
        if include_combos:
            brand_data['matched_combos_details'] = get_matched_combos(brandid)
        
        # Add sample narratives if requested
        if include_narratives:
            brand_data['sample_narratives'] = get_sample_narratives(brandid, sample_size)
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(brand_data)
        }
    
    except Exception as e:
        print(f"Error retrieving brand data: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }


def get_brand_metadata(brandid: int) -> Dict[str, Any]:
    """Retrieve brand metadata from S3."""
    try:
        s3_key = f"metadata/brand_{brandid}.json"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        metadata = json.loads(response['Body'].read().decode('utf-8'))
        
        return metadata
    
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        print(f"Error retrieving brand metadata: {str(e)}")
        return None


def get_matched_combos(brandid: int) -> Dict[str, Any]:
    """Get matched combo details for the brand."""
    try:
        # Retrieve from S3 metadata
        s3_key = f"metadata/brand_{brandid}.json"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        metadata = json.loads(response['Body'].read().decode('utf-8'))
        
        matched_combos = metadata.get('matched_combos', {})
        
        return {
            'confirmed_count': len(matched_combos.get('confirmed', [])),
            'excluded_count': len(matched_combos.get('excluded', [])),
            'ties_resolved_count': len(matched_combos.get('ties_resolved', [])),
            'requires_review_count': len(matched_combos.get('requires_human_review', [])),
            'confirmed_combos': matched_combos.get('confirmed', [])[:10],  # First 10
            'excluded_combos': matched_combos.get('excluded', [])[:10],  # First 10
            'requires_review_combos': matched_combos.get('requires_human_review', [])[:10]  # First 10
        }
    
    except Exception as e:
        print(f"Error getting matched combos: {str(e)}")
        return {
            'confirmed_count': 0,
            'excluded_count': 0,
            'ties_resolved_count': 0,
            'requires_review_count': 0,
            'confirmed_combos': [],
            'excluded_combos': [],
            'requires_review_combos': []
        }


def get_sample_narratives(brandid: int, sample_size: int) -> Dict[str, Any]:
    """Get sample narratives for the brand from Athena."""
    try:
        # Query Athena for sample narratives
        query = f"""
        SELECT narrative, mccid, ccid, bankid
        FROM {ATHENA_DATABASE}.combo
        WHERE brandid = {brandid}
        LIMIT {sample_size}
        """
        
        # Execute query
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': ATHENA_DATABASE},
            ResultConfiguration={'OutputLocation': f's3://{S3_BUCKET}/athena-results/'}
        )
        
        query_execution_id = response['QueryExecutionId']
        
        # Wait for query to complete (simplified - in production, use polling)
        import time
        time.sleep(2)
        
        # Get query results
        results = athena_client.get_query_results(QueryExecutionId=query_execution_id)
        
        narratives = []
        for row in results['ResultSet']['Rows'][1:]:  # Skip header row
            data = row['Data']
            narratives.append({
                'narrative': data[0].get('VarCharValue', ''),
                'mccid': int(data[1].get('VarCharValue', 0)),
                'ccid': int(data[2].get('VarCharValue', 0)),
                'bankid': int(data[3].get('VarCharValue', 0))
            })
        
        return {
            'sample_size': len(narratives),
            'narratives': narratives
        }
    
    except Exception as e:
        print(f"Error getting sample narratives: {str(e)}")
        return {
            'sample_size': 0,
            'narratives': []
        }

