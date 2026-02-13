"""
Lambda function to invoke the Orchestrator Agent.

This function serves as the bridge between Step Functions and the
Bedrock AgentCore Orchestrator Agent.
"""

import json
import os
import boto3
from typing import Dict, Any


# Initialize AWS clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=os.environ.get("AWS_REGION", "eu-west-1"))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Invoke Orchestrator Agent to coordinate workflow.
    
    Args:
        event: Input event containing workflow config and state
        context: Lambda context object
        
    Returns:
        Dictionary with orchestrator execution results
    """
    try:
        # Extract configuration and state
        workflow_config = event.get("workflow_config", {}).get("config", {})
        workflow_state = event.get("workflow_config", {}).get("state", {})
        
        # Get agent ID from environment
        agent_id = os.environ.get("ORCHESTRATOR_AGENT_ID")
        agent_alias_id = os.environ.get("ORCHESTRATOR_AGENT_ALIAS_ID", "TSTALIASID")
        
        if not agent_id:
            raise ValueError("ORCHESTRATOR_AGENT_ID environment variable not set")
        
        # Prepare input for orchestrator
        orchestrator_input = {
            "action": "start_workflow",
            "config": workflow_config,
            "workflow_id": workflow_state.get("workflow_id"),
            "session_id": context.request_id
        }
        
        # Invoke Bedrock Agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=context.request_id,
            inputText=json.dumps(orchestrator_input)
        )
        
        # Process streaming response
        result_text = ""
        for event_chunk in response.get('completion', []):
            if 'chunk' in event_chunk:
                chunk_data = event_chunk['chunk']
                if 'bytes' in chunk_data:
                    result_text += chunk_data['bytes'].decode('utf-8')
        
        # Parse result
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            # If not JSON, wrap in response
            result = {
                "status": "completed",
                "message": result_text
            }
        
        return {
            "statusCode": 200,
            "status": result.get("status", "completed"),
            "succeeded_brands": result.get("succeeded_brands", []),
            "failed_brands": result.get("failed_brands", []),
            "brands_requiring_review": result.get("brands_requiring_review", []),
            "summary": result.get("summary", {}),
            "message": result.get("message", "Orchestrator completed successfully")
        }
        
    except ValueError as e:
        return {
            "statusCode": 400,
            "status": "failed",
            "error": "ValidationError",
            "message": str(e)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "status": "failed",
            "error": "OrchestratorInvocationError",
            "message": f"Failed to invoke orchestrator: {str(e)}"
        }
