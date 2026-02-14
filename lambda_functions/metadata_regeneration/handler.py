"""
Lambda function to regenerate metadata based on feedback.

This function invokes the Metadata Production Agent with refinement prompts
to regenerate improved metadata.
"""

import json
import os
import boto3
from typing import Dict, Any, List

# Initialize AWS clients
bedrock_agent = boto3.client('bedrock-agent-runtime', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
S3_BUCKET = os.environ.get('S3_BUCKET', 'brand-generator-rwrd-023-eu-west-1')
METADATA_PRODUCTION_AGENT_ID = os.environ.get('METADATA_PRODUCTION_AGENT_ID')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Regenerate metadata based on refinement prompts.
    
    Input:
    {
        "brands_to_regenerate": [int],
        "refinement_prompts": {
            "brandid": str
        },
        "workflow_config": {...},
        "iteration": int
    }
    
    Output:
    {
        "status": "success",
        "regenerated_brands": [int]
    }
    """
    try:
        brands_to_regenerate = event.get('brands_to_regenerate', [])
        refinement_prompts = event.get('refinement_prompts', {})
        workflow_config = event.get('workflow_config', {})
        iteration = event.get('iteration', 1)
        
        if not brands_to_regenerate:
            return {
                'statusCode': 200,
                'status': 'no_brands_to_regenerate',
                'regenerated_brands': []
            }
        
        # Regenerate metadata for each brand
        regenerated_brands = []
        
        for brandid in brands_to_regenerate:
            refinement_prompt = refinement_prompts.get(str(brandid), '')
            
            # Get current metadata and brand data
            current_metadata = get_current_metadata(brandid)
            brand_data = get_brand_data(brandid)
            
            # Invoke Metadata Production Agent
            success = regenerate_brand_metadata(
                brandid=brandid,
                refinement_prompt=refinement_prompt,
                current_metadata=current_metadata,
                brand_data=brand_data,
                iteration=iteration
            )
            
            if success:
                regenerated_brands.append(brandid)
        
        return {
            'statusCode': 200,
            'status': 'success',
            'regenerated_brands': regenerated_brands
        }
    
    except Exception as e:
        print(f"Error regenerating metadata: {str(e)}")
        return {
            'statusCode': 500,
            'status': 'error',
            'error': str(e)
        }


def get_current_metadata(brandid: int) -> Dict[str, Any]:
    """Retrieve current metadata for the brand from S3."""
    try:
        s3_key = f"metadata/brand_{brandid}.json"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        metadata = json.loads(response['Body'].read().decode('utf-8'))
        return metadata
    except s3_client.exceptions.NoSuchKey:
        return {}
    except Exception as e:
        print(f"Error retrieving metadata for brand {brandid}: {str(e)}")
        return {}


def get_brand_data(brandid: int) -> Dict[str, Any]:
    """Get brand data from S3."""
    try:
        s3_key = f"brand_data/brand_{brandid}.json"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        brand_data = json.loads(response['Body'].read().decode('utf-8'))
        return brand_data
    except s3_client.exceptions.NoSuchKey:
        return {}
    except Exception as e:
        print(f"Error retrieving brand data for {brandid}: {str(e)}")
        return {}


def regenerate_brand_metadata(
    brandid: int,
    refinement_prompt: str,
    current_metadata: Dict[str, Any],
    brand_data: Dict[str, Any],
    iteration: int
) -> bool:
    """Regenerate metadata for a brand using Metadata Production Agent."""
    try:
        # Prepare input for Metadata Production Agent
        agent_input = {
            "action": "regenerate_metadata",
            "brandid": brandid,
            "refinement_prompt": refinement_prompt,
            "current_metadata": current_metadata,
            "brand_data": brand_data,
            "iteration": iteration
        }
        
        # Invoke Metadata Production Agent
        if METADATA_PRODUCTION_AGENT_ID:
            response = bedrock_agent.invoke_agent(
                agentId=METADATA_PRODUCTION_AGENT_ID,
                agentAliasId='TSTALIASID',
                sessionId=f"metadata-regen-{brandid}-{iteration}",
                inputText=json.dumps(agent_input)
            )
            
            # Parse agent response
            new_metadata = {}
            for event in response.get('completion', []):
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        new_metadata = json.loads(chunk['bytes'].decode('utf-8'))
            
            # Store new metadata version
            if new_metadata:
                store_metadata_version(brandid, new_metadata, iteration)
                return True
        
        return False
    
    except Exception as e:
        print(f"Error regenerating metadata for brand {brandid}: {str(e)}")
        return False


def store_metadata_version(brandid: int, metadata: Dict[str, Any], iteration: int) -> None:
    """Store new metadata version in S3."""
    try:
        # Store versioned metadata
        s3_key = f"metadata/brand_{brandid}_v{iteration}.json"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(metadata),
            ContentType='application/json'
        )
        
        # Update current metadata
        s3_key_current = f"metadata/brand_{brandid}.json"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key_current,
            Body=json.dumps(metadata),
            ContentType='application/json'
        )
    except Exception as e:
        print(f"Error storing metadata version: {str(e)}")
        raise

