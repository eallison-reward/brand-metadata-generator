"""
Lambda function to reapply regenerated metadata to combos.

This function applies the regenerated metadata to combos and re-runs
the classification agents.
"""

import json
import os
import boto3
from typing import Dict, Any, List

# Initialize AWS clients
bedrock_agent = boto3.client('bedrock-agent-runtime', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
DATA_TRANSFORMATION_AGENT_ID = os.environ.get('DATA_TRANSFORMATION_AGENT_ID')
CONFIRMATION_AGENT_ID = os.environ.get('CONFIRMATION_AGENT_ID')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Reapply regenerated metadata to combos and re-run classification.
    
    Input:
    {
        "regenerated_brands": [int],
        "workflow_config": {...}
    }
    
    Output:
    {
        "status": "success",
        "brands_reclassified": [int]
    }
    """
    try:
        regenerated_brands = event.get('regenerated_brands', [])
        workflow_config = event.get('workflow_config', {})
        
        if not regenerated_brands:
            return {
                'statusCode': 200,
                'status': 'no_brands_to_reclassify',
                'brands_reclassified': []
            }
        
        # Reapply metadata for each brand
        brands_reclassified = []
        
        for brandid in regenerated_brands:
            # Apply metadata to combos
            apply_success = apply_metadata_to_combos(brandid)
            
            if apply_success:
                # Re-run confirmation agent
                confirm_success = run_confirmation_agent(brandid)
                
                if confirm_success:
                    brands_reclassified.append(brandid)
        
        return {
            'statusCode': 200,
            'status': 'success',
            'brands_reclassified': brands_reclassified
        }
    
    except Exception as e:
        print(f"Error reapplying metadata: {str(e)}")
        return {
            'statusCode': 500,
            'status': 'error',
            'error': str(e)
        }


def apply_metadata_to_combos(brandid: int) -> bool:
    """Apply metadata to combos using Data Transformation Agent."""
    try:
        # Prepare input for Data Transformation Agent
        agent_input = {
            "action": "apply_metadata_to_combos",
            "brandid": brandid
        }
        
        # Invoke Data Transformation Agent
        if DATA_TRANSFORMATION_AGENT_ID:
            response = bedrock_agent.invoke_agent(
                agentId=DATA_TRANSFORMATION_AGENT_ID,
                agentAliasId='TSTALIASID',
                sessionId=f"apply-metadata-{brandid}",
                inputText=json.dumps(agent_input)
            )
            
            # Parse agent response
            for event in response.get('completion', []):
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        result = json.loads(chunk['bytes'].decode('utf-8'))
                        if result.get('status') == 'success':
                            return True
        
        return False
    
    except Exception as e:
        print(f"Error applying metadata for brand {brandid}: {str(e)}")
        return False


def run_confirmation_agent(brandid: int) -> bool:
    """Run Confirmation Agent to review matched combos."""
    try:
        # Prepare input for Confirmation Agent
        agent_input = {
            "action": "review_matches",
            "brandid": brandid
        }
        
        # Invoke Confirmation Agent
        if CONFIRMATION_AGENT_ID:
            response = bedrock_agent.invoke_agent(
                agentId=CONFIRMATION_AGENT_ID,
                agentAliasId='TSTALIASID',
                sessionId=f"confirmation-{brandid}",
                inputText=json.dumps(agent_input)
            )
            
            # Parse agent response
            for event in response.get('completion', []):
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        result = json.loads(chunk['bytes'].decode('utf-8'))
                        if result.get('confirmed_combos') is not None:
                            return True
        
        return False
    
    except Exception as e:
        print(f"Error running confirmation for brand {brandid}: {str(e)}")
        return False

