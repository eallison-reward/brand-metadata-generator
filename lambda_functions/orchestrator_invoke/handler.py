"""
Lambda function to invoke the Orchestrator Agent.

This function serves as the bridge between Step Functions and the
Bedrock AgentCore Orchestrator Agent.
"""

import json
import os
import boto3
from typing import Dict, Any


# Initialize Bedrock AgentCore client
bedrock_agentcore = boto3.client('bedrock-agentcore', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))


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
        brandid = event.get("brandid")
        
        # Get agent ARN from environment
        agent_arn = os.environ.get("ORCHESTRATOR_AGENT_ARN")
        
        if not agent_arn:
            raise ValueError("ORCHESTRATOR_AGENT_ARN environment variable not set")
        
        # Prepare input for orchestrator
        orchestrator_input = {
            "action": "start_workflow",
            "brandid": brandid,
            "config": workflow_config,
            "workflow_id": workflow_state.get("workflow_id"),
            "session_id": context.aws_request_id
        }
        
        # Convert input to JSON payload
        payload = json.dumps(orchestrator_input).encode('utf-8')
        
        print(f"Invoking orchestrator agent ARN: {agent_arn}")
        print(f"Processing brand: {brandid}")
        print(f"Payload: {orchestrator_input}")
        
        # Invoke the orchestrator agent using AgentCore API
        response = bedrock_agentcore.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            runtimeSessionId=f"workflow-{workflow_state.get('workflow_id', context.aws_request_id)}",
            contentType='application/json',
            accept='application/json',
            payload=payload
        )
        
        # Read the streaming response
        response_body = b''
        if 'response' in response:
            response_stream = response['response']
            if hasattr(response_stream, 'read'):
                response_body = response_stream.read()
            else:
                # Handle EventStream
                for event in response_stream:
                    if 'chunk' in event:
                        response_body += event['chunk'].get('bytes', b'')
        
        response_text = response_body.decode('utf-8')
        print(f"Orchestrator response: {response_text}")
        
        # Try to parse response as JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # If response is not JSON, extract information from text
            print("Response is not JSON, parsing as text")
            result = {
                "status": "completed" if "success" in response_text.lower() or "completed" in response_text.lower() else "failed",
                "succeeded_brands": [brandid] if "success" in response_text.lower() or "completed" in response_text.lower() else [],
                "failed_brands": [] if "success" in response_text.lower() or "completed" in response_text.lower() else [brandid],
                "brands_requiring_review": [],
                "summary": {
                    "total_brands": 1,
                    "succeeded": 1 if "success" in response_text.lower() or "completed" in response_text.lower() else 0,
                    "failed": 0 if "success" in response_text.lower() or "completed" in response_text.lower() else 1,
                    "requires_review": 0
                },
                "raw_response": response_text
            }
        
        # Ensure required fields exist
        result.setdefault("statusCode", 200)
        result.setdefault("status", "completed")
        result.setdefault("succeeded_brands", [])
        result.setdefault("failed_brands", [])
        result.setdefault("brands_requiring_review", [])
        result.setdefault("summary", {
            "total_brands": 0,
            "succeeded": 0,
            "failed": 0,
            "requires_review": 0
        })
        
        return result
        
    except ValueError as e:
        print(f"Validation error: {e}")
        return {
            "statusCode": 400,
            "status": "failed",
            "error": "ValidationError",
            "message": str(e),
            "succeeded_brands": [],
            "failed_brands": [event.get("brandid")] if event.get("brandid") else [],
            "brands_requiring_review": [],
            "summary": {
                "total_brands": 1 if event.get("brandid") else 0,
                "succeeded": 0,
                "failed": 1 if event.get("brandid") else 0,
                "requires_review": 0
            }
        }
    except Exception as e:
        print(f"Orchestrator invocation error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "statusCode": 500,
            "status": "failed",
            "error": "OrchestratorInvocationError",
            "message": f"Failed to invoke orchestrator: {str(e)}",
            "succeeded_brands": [],
            "failed_brands": [event.get("brandid")] if event.get("brandid") else [],
            "brands_requiring_review": [],
            "summary": {
                "total_brands": 1 if event.get("brandid") else 0,
                "succeeded": 0,
                "failed": 1 if event.get("brandid") else 0,
                "requires_review": 0
            }
        }
