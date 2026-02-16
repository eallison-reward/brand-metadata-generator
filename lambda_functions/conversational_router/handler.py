"""Router Lambda for Conversational Interface Agent.

This Lambda function routes action group requests from the Bedrock Agent
to the appropriate tool Lambda function based on the operationId (tool name).
"""

import json
import os
import boto3
from typing import Dict, Any

# Initialize Lambda client
lambda_client = boto3.client('lambda')

# Environment variables
ENV = os.environ.get('ENV', 'dev')
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-1')

# Map tool names to Lambda function names
TOOL_TO_LAMBDA = {
    'get_help': f'brand_metagen_get_help_{ENV}',
    'query_brands_to_check': f'brand_metagen_query_brands_to_check_{ENV}',
    'start_workflow': f'brand_metagen_start_workflow_{ENV}',
    'check_workflow_status': f'brand_metagen_check_workflow_status_{ENV}',
    'submit_feedback': f'brand_metagen_submit_feedback_{ENV}',
    'query_metadata': f'brand_metagen_query_metadata_{ENV}',
    'execute_athena_query': f'brand_metagen_execute_athena_query_{ENV}',
    'list_escalations': f'brand_metagen_list_escalations_{ENV}',
    'get_workflow_stats': f'brand_metagen_get_workflow_stats_{ENV}',
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Route Bedrock Agent action group requests to appropriate tool Lambda.
    
    Args:
        event: Bedrock Agent action group event
        context: Lambda context
        
    Returns:
        Response in Bedrock Agent action group format
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract action group information
        action_group = event.get('actionGroup', '')
        api_path = event.get('apiPath', '')
        http_method = event.get('httpMethod', '')
        parameters = event.get('parameters', [])
        request_body = event.get('requestBody', {})
        
        # Extract tool name from apiPath (e.g., "/query_brands_to_check" -> "query_brands_to_check")
        tool_name = api_path.lstrip('/')
        
        print(f"Routing to tool: {tool_name}")
        
        # Get target Lambda function name
        target_function = TOOL_TO_LAMBDA.get(tool_name)
        
        if not target_function:
            error_msg = f"Unknown tool: {tool_name}"
            print(f"ERROR: {error_msg}")
            return create_error_response(error_msg)
        
        # Convert parameters array to dict
        params_dict = {}
        for param in parameters:
            param_name = param.get('name')
            param_value = param.get('value')
            param_type = param.get('type', 'string')
            if param_name and param_value is not None:
                # Convert parameter value based on type
                params_dict[param_name] = convert_parameter_value(param_value, param_type)
        
        # Merge with request body content if present
        if request_body and 'content' in request_body:
            content = request_body['content']
            if isinstance(content, dict):
                for content_type, content_data in content.items():
                    if isinstance(content_data, dict) and 'properties' in content_data:
                        for prop in content_data['properties']:
                            prop_name = prop.get('name')
                            prop_value = prop.get('value')
                            prop_type = prop.get('type', 'string')
                            if prop_name and prop_value is not None:
                                # Convert parameter value based on type
                                params_dict[prop_name] = convert_parameter_value(prop_value, prop_type)
        
        print(f"Invoking {target_function} with parameters: {params_dict}")
        
        # Invoke target Lambda function
        response = lambda_client.invoke(
            FunctionName=target_function,
            InvocationType='RequestResponse',
            Payload=json.dumps(params_dict)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        print(f"Tool response: {json.dumps(response_payload)}")
        
        # Check if tool returned an error
        if response.get('FunctionError'):
            error_msg = response_payload.get('errorMessage', 'Unknown error')
            print(f"ERROR from tool: {error_msg}")
            return create_error_response(error_msg)
        
        # Return success response in Bedrock Agent format
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': action_group,
                'apiPath': api_path,
                'httpMethod': http_method,
                'httpStatusCode': 200,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(response_payload)
                    }
                }
            }
        }
        
    except Exception as e:
        error_msg = f"Router error: {str(e)}"
        print(f"ERROR: {error_msg}")
        return create_error_response(error_msg)


def convert_parameter_value(value: Any, param_type: str) -> Any:
    """Convert parameter value to the correct type.
    
    Args:
        value: Parameter value (usually string)
        param_type: Parameter type (string, integer, boolean, object, array)
        
    Returns:
        Converted value
    """
    # Auto-detect arrays/objects in string format even if type is not specified
    if isinstance(value, str):
        # Try to parse as JSON if it looks like JSON
        if (value.startswith('[') and value.endswith(']')) or \
           (value.startswith('{') and value.endswith('}')):
            try:
                parsed = json.loads(value)
                print(f"Auto-parsed JSON string: {value} -> {parsed}")
                return parsed
            except json.JSONDecodeError:
                pass
        
        # Try to convert numeric strings to integers if they look like integers
        if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            try:
                int_value = int(value)
                print(f"Auto-converted numeric string: {value} -> {int_value}")
                return int_value
            except ValueError:
                pass
    
    if param_type == 'integer':
        try:
            return int(value)
        except (ValueError, TypeError):
            return value
    elif param_type == 'boolean':
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    elif param_type == 'object':
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value
    elif param_type == 'array':
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # Try to split by comma
                return [item.strip() for item in value.split(',')]
        return value
    else:
        # Default to string (but already handled JSON parsing above)
        return str(value) if value is not None else value


def create_error_response(error_message: str) -> Dict[str, Any]:
    """Create error response in Bedrock Agent format.
    
    Args:
        error_message: Error message
        
    Returns:
        Error response dict
    """
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': '',
            'apiPath': '',
            'httpMethod': '',
            'httpStatusCode': 500,
            'responseBody': {
                'application/json': {
                    'body': json.dumps({
                        'error': error_message
                    })
                }
            }
        }
    }
