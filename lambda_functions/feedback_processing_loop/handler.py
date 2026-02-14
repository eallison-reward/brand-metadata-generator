"""
Lambda function to process feedback and generate refinement prompts.

This function invokes the Feedback Processing Agent to analyze feedback
and generate refinement prompts for metadata regeneration.
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
FEEDBACK_AGENT_ID = os.environ.get('FEEDBACK_AGENT_ID')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process feedback and generate refinement prompts.
    
    Input:
    {
        "brands_rejected": [int],
        "feedback_data": {
            "brandid": {
                "feedback_text": str,
                "misclassified_combos": [int]
            }
        },
        "workflow_config": {...}
    }
    
    Output:
    {
        "status": "success",
        "refinement_prompts": {
            "brandid": str
        },
        "brands_to_regenerate": [int]
    }
    """
    try:
        brands_rejected = event.get('brands_rejected', [])
        feedback_data = event.get('feedback_data', {})
        workflow_config = event.get('workflow_config', {})
        
        if not brands_rejected:
            return {
                'statusCode': 200,
                'status': 'no_brands_to_process',
                'refinement_prompts': {},
                'brands_to_regenerate': []
            }
        
        # Process feedback for each brand
        refinement_prompts = {}
        brands_to_regenerate = []
        
        for brandid in brands_rejected:
            brand_feedback = feedback_data.get(str(brandid), {})
            
            # Get current metadata
            current_metadata = get_current_metadata(brandid)
            
            # Invoke Feedback Processing Agent
            refinement_prompt = process_brand_feedback(
                brandid=brandid,
                feedback_text=brand_feedback.get('feedback_text', ''),
                misclassified_combos=brand_feedback.get('misclassified_combos', []),
                current_metadata=current_metadata
            )
            
            if refinement_prompt:
                refinement_prompts[str(brandid)] = refinement_prompt
                brands_to_regenerate.append(brandid)
        
        return {
            'statusCode': 200,
            'status': 'success',
            'refinement_prompts': refinement_prompts,
            'brands_to_regenerate': brands_to_regenerate
        }
    
    except Exception as e:
        print(f"Error processing feedback: {str(e)}")
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


def process_brand_feedback(
    brandid: int,
    feedback_text: str,
    misclassified_combos: List[int],
    current_metadata: Dict[str, Any]
) -> str:
    """Process feedback for a brand and generate refinement prompt."""
    try:
        # Prepare input for Feedback Processing Agent
        agent_input = {
            "action": "process_feedback",
            "brandid": brandid,
            "feedback_type": "specific_examples" if misclassified_combos else "general",
            "feedback_text": feedback_text,
            "misclassified_combos": misclassified_combos,
            "current_metadata": current_metadata
        }
        
        # Invoke Feedback Processing Agent
        if FEEDBACK_AGENT_ID:
            response = bedrock_agent.invoke_agent(
                agentId=FEEDBACK_AGENT_ID,
                agentAliasId='TSTALIASID',
                sessionId=f"feedback-processing-{brandid}",
                inputText=json.dumps(agent_input)
            )
            
            # Parse agent response
            refinement_prompt = ""
            for event in response.get('completion', []):
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        result = json.loads(chunk['bytes'].decode('utf-8'))
                        refinement_prompt = result.get('refinement_prompt', '')
            
            return refinement_prompt
        else:
            # Fallback: Generate basic refinement prompt
            return f"Regenerate metadata for brand {brandid} based on feedback: {feedback_text}"
    
    except Exception as e:
        print(f"Error processing feedback for brand {brandid}: {str(e)}")
        return f"Regenerate metadata for brand {brandid}"

