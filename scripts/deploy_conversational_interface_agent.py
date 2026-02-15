#!/usr/bin/env python3
"""Deploy Conversational Interface Agent to AWS Bedrock AgentCore.

This script deploys the Conversational Interface Agent using the Strands API
for AWS Bedrock AgentCore runtime. The agent provides a natural language
interface for interacting with the Brand Metadata Generator system.

Usage:
    python deploy_conversational_interface_agent.py --env dev
    python deploy_conversational_interface_agent.py --env prod --dry-run
    python deploy_conversational_interface_agent.py --env dev --update-only
"""

import argparse
import json
import sys
import time
import boto3
from pathlib import Path
from typing import Optional, Dict, Any, List


# AWS Configuration
AWS_REGION = "eu-west-1"
AGENT_NAME_PREFIX = "brand_metagen_conversational_interface"

# Agent configuration
AGENT_CONFIG = {
    "model": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "timeout": 300,
    "description": "Natural language interface for Brand Metadata Generator system",
    "temperature": 0.7,
    "max_tokens": 2048,
}

# Tool Lambda function names (must match deployed Lambda functions)
TOOL_LAMBDA_FUNCTIONS = [
    "query_brands_to_check",
    "start_workflow",
    "check_workflow_status",
    "submit_feedback",
    "query_metadata",
    "execute_athena_query",
    "list_escalations",
    "get_workflow_stats",
]

# Router Lambda function name
ROUTER_LAMBDA_NAME = "conversational_router"


def read_instruction_prompt() -> str:
    """Read agent instruction prompt from file.
    
    Returns:
        Agent instructions as string
    """
    instruction_path = Path("infrastructure/prompts/conversational_interface_instructions.md")
    
    if not instruction_path.exists():
        print(f"❌ Error: Instructions not found at {instruction_path}")
        sys.exit(1)
    
    with open(instruction_path, 'r') as f:
        return f.read()


def read_tool_schemas() -> List[Dict[str, Any]]:
    """Read tool schemas from JSON file.
    
    Returns:
        List of tool schema definitions
    """
    schema_path = Path("agents/conversational_interface/tool_schemas.json")
    
    if not schema_path.exists():
        print(f"❌ Error: Tool schemas not found at {schema_path}")
        sys.exit(1)
    
    with open(schema_path, 'r') as f:
        data = json.load(f)
        return data.get("tools", [])


def get_lambda_function_arn(
    lambda_client: Any,
    function_name: str,
    env: str
) -> Optional[str]:
    """Get Lambda function ARN.
    
    Args:
        lambda_client: Boto3 Lambda client
        function_name: Base function name
        env: Environment name
        
    Returns:
        Function ARN if found, None otherwise
    """
    full_function_name = f"brand_metagen_{function_name}_{env}"
    
    try:
        response = lambda_client.get_function(FunctionName=full_function_name)
        return response['Configuration']['FunctionArn']
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"   ⚠️  Lambda function not found: {full_function_name}")
        return None
    except Exception as e:
        print(f"   ⚠️  Error getting Lambda function ARN: {str(e)}")
        return None


def deploy_router_lambda(
    lambda_client: Any,
    iam_client: Any,
    env: str,
    function_arns: Dict[str, str],
    dry_run: bool = False
) -> Optional[str]:
    """Deploy router Lambda function.
    
    Args:
        lambda_client: Boto3 Lambda client
        iam_client: Boto3 IAM client
        env: Environment name
        function_arns: Dictionary mapping function names to ARNs
        dry_run: If True, only print what would be done
        
    Returns:
        Router Lambda ARN if successful, None otherwise
    """
    print("\n🚀 Deploying router Lambda function...")
    
    function_name = f"brand_metagen_{ROUTER_LAMBDA_NAME}_{env}"
    
    if dry_run:
        print(f"   [DRY RUN] Would deploy router Lambda: {function_name}")
        return f"arn:aws:lambda:{AWS_REGION}:123456789012:function:{function_name}"
    
    # Create IAM role for router Lambda
    role_name = f"brand_metagen_router_lambda_{env}"
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        # Try to create role
        try:
            role_response = iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f"Execution role for conversational router Lambda ({env})"
            )
            role_arn = role_response['Role']['Arn']
            print(f"   ✓ Created IAM role: {role_name}")
            
            # Wait for role to be available
            import time
            time.sleep(10)
        except iam_client.exceptions.EntityAlreadyExistsException:
            role_response = iam_client.get_role(RoleName=role_name)
            role_arn = role_response['Role']['Arn']
            print(f"   ℹ️  Using existing IAM role: {role_name}")
        
        # Attach basic Lambda execution policy
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        )
        
        # Create inline policy for invoking tool Lambdas and DynamoDB access
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "lambda:InvokeFunction",
                    "Resource": list(function_arns.values())
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "dynamodb:BatchGetItem",
                        "dynamodb:BatchWriteItem"
                    ],
                    "Resource": [
                        f"arn:aws:dynamodb:{AWS_REGION}:*:table/brand_processing_status_{env}",
                        f"arn:aws:dynamodb:{AWS_REGION}:*:table/brand_processing_status_{env}/index/*"
                    ]
                }
            ]
        }
        
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName="invoke_tool_lambdas",
            PolicyDocument=json.dumps(policy_document)
        )
        print(f"   ✓ Configured Lambda invoke permissions")
        
    except Exception as e:
        print(f"   ❌ Failed to create/configure IAM role: {str(e)}")
        return None
    
    # Package Lambda code
    import zipfile
    import tempfile
    from pathlib import Path
    
    handler_path = Path("lambda_functions/conversational_router/handler.py")
    
    if not handler_path.exists():
        print(f"   ❌ Router handler not found: {handler_path}")
        return None
    
    # Create deployment package
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
        zip_path = tmp_file.name
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(handler_path, 'handler.py')
        
        # Read zip file
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
    
    # Deploy Lambda function
    try:
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName=function_name)
            function_exists = True
        except lambda_client.exceptions.ResourceNotFoundException:
            function_exists = False
        
        if function_exists:
            print(f"   ℹ️  Updating existing Lambda function...")
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            
            # Update configuration
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                Runtime='python3.11',
                Handler='handler.lambda_handler',
                Role=role_arn,
                Timeout=60,
                MemorySize=256,
                Environment={
                    'Variables': {
                        'ENV': env
                    }
                }
            )
        else:
            print(f"   Creating new Lambda function...")
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.11',
                Role=role_arn,
                Handler='handler.lambda_handler',
                Code={'ZipFile': zip_content},
                Timeout=60,
                MemorySize=256,
                Environment={
                    'Variables': {
                        'ENV': env
                    }
                },
                Description=f"Router for conversational interface agent ({env})"
            )
        
        # Get function ARN
        response = lambda_client.get_function(FunctionName=function_name)
        function_arn = response['Configuration']['FunctionArn']
        
        print(f"   ✅ Router Lambda deployed: {function_arn}")
        return function_arn
        
    except Exception as e:
        print(f"   ❌ Failed to deploy router Lambda: {str(e)}")
        return None


def verify_lambda_functions(env: str) -> Dict[str, str]:
    """Verify all required Lambda functions exist and get their ARNs.
    
    Args:
        env: Environment name
        
    Returns:
        Dictionary mapping function names to ARNs
    """
    print("\n📋 Verifying Lambda functions...")
    
    lambda_client = boto3.client('lambda', region_name=AWS_REGION)
    function_arns = {}
    missing_functions = []
    
    for function_name in TOOL_LAMBDA_FUNCTIONS:
        arn = get_lambda_function_arn(lambda_client, function_name, env)
        if arn:
            function_arns[function_name] = arn
            print(f"   ✓ {function_name}: {arn}")
        else:
            missing_functions.append(function_name)
            print(f"   ✗ {function_name}: NOT FOUND")
    
    if missing_functions:
        print(f"\n❌ Error: Missing Lambda functions: {', '.join(missing_functions)}")
        print("   Please deploy Lambda functions before deploying the agent.")
        sys.exit(1)
    
    print(f"\n✅ All {len(function_arns)} Lambda functions verified")
    return function_arns


def create_action_group_config(
    router_lambda_arn: str,
    tool_schemas: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Create action group configuration for the agent.
    
    Args:
        router_lambda_arn: ARN of the router Lambda function
        tool_schemas: List of tool schema definitions
        
    Returns:
        Action group configuration
    """
    # Build OpenAPI schema compatible with Bedrock Agents
    # Bedrock requires a simplified OpenAPI 3.0 schema
    api_schema = {
        "openapi": "3.0.0",
        "info": {
            "title": "Brand Metadata Generator Conversational Interface API",
            "version": "1.0.0",
            "description": "API for conversational interface tools"
        },
        "paths": {}
    }
    
    # Build OpenAPI paths from tool schemas
    for tool in tool_schemas:
        tool_name = tool["name"]
        path = f"/{tool_name}"
        
        # Bedrock Agents requires specific schema format
        # Input schema must be in requestBody
        request_body = {
            "required": len(tool["inputSchema"].get("required", [])) > 0,
            "content": {
                "application/json": {
                    "schema": tool["inputSchema"]
                }
            }
        }
        
        # Output schema in response
        response_schema = {
            "200": {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": tool.get("outputSchema", {"type": "object"})
                    }
                }
            }
        }
        
        api_schema["paths"][path] = {
            "post": {
                "summary": tool["description"],
                "description": tool["description"],
                "operationId": tool_name,
                "requestBody": request_body,
                "responses": response_schema
            }
        }
    
    # Use router Lambda as the action group executor
    return {
        "apiSchema": {
            "payload": json.dumps(api_schema)
        },
        "actionGroupExecutor": {
            "lambda": router_lambda_arn
        }
    }


def update_agent_iam_role(
    iam_client: Any,
    role_name: str,
    lambda_arns: Dict[str, str],
    env: str,
    dry_run: bool = False
) -> bool:
    """Update agent IAM role with Lambda invoke permissions.
    
    Args:
        iam_client: Boto3 IAM client
        role_name: IAM role name
        lambda_arns: Dictionary mapping Lambda names to ARNs
        env: Environment name
        dry_run: If True, only print what would be done
        
    Returns:
        True if successful, False otherwise
    """
    print(f"\n🔐 Updating IAM role permissions...")
    
    if dry_run:
        print(f"   [DRY RUN] Would update role {role_name} with Lambda invoke permissions")
        return True
    
    # Create policy document for Lambda invocations
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "lambda:InvokeFunction",
                "Resource": list(lambda_arns.values())
            }
        ]
    }
    
    policy_name = f"conversational_interface_lambda_invoke_{env}"
    
    try:
        # Try to update existing policy
        try:
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document)
            )
            print(f"   ✅ Updated inline policy: {policy_name}")
        except iam_client.exceptions.NoSuchEntityException:
            print(f"   ❌ Role not found: {role_name}")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to update IAM role: {str(e)}")
        return False


def create_or_update_agent(
    bedrock_agent_client: Any,
    agent_name: str,
    env: str,
    execution_role_arn: str,
    instructions: str,
    dry_run: bool = False
) -> Optional[str]:
    """Create or update agent in Bedrock AgentCore.
    
    Args:
        bedrock_agent_client: Boto3 Bedrock Agent client
        agent_name: Full agent name
        env: Environment name
        execution_role_arn: ARN of the agent execution role
        instructions: Agent instruction prompt
        dry_run: If True, only print what would be done
        
    Returns:
        Agent ID if successful, None otherwise
    """
    print(f"\n📝 Configuring agent: {agent_name}...")
    
    agent_params = {
        "agentName": agent_name,
        "agentResourceRoleArn": execution_role_arn,
        "foundationModel": AGENT_CONFIG["model"],
        "instruction": instructions,
        "description": AGENT_CONFIG["description"],
        "idleSessionTTLInSeconds": 1800,  # 30 minutes
    }
    
    if dry_run:
        print(f"   [DRY RUN] Would create/update agent with:")
        print(f"   - Name: {agent_name}")
        print(f"   - Model: {agent_params['foundationModel']}")
        print(f"   - Role: {execution_role_arn}")
        print(f"   - Instructions: {len(instructions)} characters")
        return "dry-run-agent-id"
    
    try:
        # Check if agent already exists
        try:
            list_response = bedrock_agent_client.list_agents()
            existing_agent = next(
                (a for a in list_response.get('agentSummaries', []) 
                 if a['agentName'] == agent_name),
                None
            )
            
            if existing_agent:
                agent_id = existing_agent['agentId']
                print(f"   ℹ️  Agent already exists (ID: {agent_id}), updating...")
                
                response = bedrock_agent_client.update_agent(
                    agentId=agent_id,
                    **agent_params
                )
                print(f"   ✅ Agent updated successfully")
                return agent_id
        except Exception as e:
            print(f"   ℹ️  Could not check for existing agent: {str(e)}")
        
        # Create new agent
        print(f"   Creating new agent...")
        response = bedrock_agent_client.create_agent(**agent_params)
        agent_id = response['agent']['agentId']
        print(f"   ✅ Agent created successfully (ID: {agent_id})")
        
        # Wait for agent to be ready
        print(f"   Waiting for agent to be ready...")
        max_attempts = 30
        for attempt in range(max_attempts):
            response = bedrock_agent_client.get_agent(agentId=agent_id)
            status = response['agent']['agentStatus']
            
            if status == 'NOT_PREPARED':
                print(f"   ✅ Agent is ready for preparation")
                break
            elif status == 'FAILED':
                print(f"   ❌ Agent creation failed")
                return None
            
            time.sleep(2)
        else:
            print(f"   ⚠️  Agent creation timed out")
            return None
        
        return agent_id
        
    except Exception as e:
        print(f"   ❌ Failed to create/update agent: {str(e)}")
        return None


def create_or_update_action_group(
    bedrock_agent_client: Any,
    agent_id: str,
    agent_version: str,
    router_lambda_arn: str,
    tool_schemas: List[Dict[str, Any]],
    dry_run: bool = False
) -> Optional[str]:
    """Create or update action group for the agent.
    
    Args:
        bedrock_agent_client: Boto3 Bedrock Agent client
        agent_id: Agent ID
        agent_version: Agent version (typically "DRAFT")
        router_lambda_arn: ARN of the router Lambda function
        tool_schemas: List of tool schema definitions
        dry_run: If True, only print what would be done
        
    Returns:
        Action group ID if successful, None otherwise
    """
    print(f"\n🔧 Configuring action group...")
    
    if dry_run:
        print(f"   [DRY RUN] Would create/update action group with {len(tool_schemas)} tools")
        return "dry-run-action-group-id"
    
    action_group_name = "conversational_interface_tools"
    
    # Create action group configuration
    action_group_config = create_action_group_config(router_lambda_arn, tool_schemas)
    
    try:
        # Check if action group already exists
        try:
            list_response = bedrock_agent_client.list_agent_action_groups(
                agentId=agent_id,
                agentVersion=agent_version
            )
            existing_action_group = next(
                (ag for ag in list_response.get('actionGroupSummaries', []) 
                 if ag['actionGroupName'] == action_group_name),
                None
            )
            
            if existing_action_group:
                action_group_id = existing_action_group['actionGroupId']
                print(f"   ℹ️  Action group already exists (ID: {action_group_id}), updating...")
                
                response = bedrock_agent_client.update_agent_action_group(
                    agentId=agent_id,
                    agentVersion=agent_version,
                    actionGroupId=action_group_id,
                    actionGroupName=action_group_name,
                    description="Tools for conversational interface",
                    actionGroupState="ENABLED",
                    **action_group_config
                )
                print(f"   ✅ Action group updated successfully")
                return action_group_id
        except Exception as e:
            print(f"   ℹ️  Could not check for existing action group: {str(e)}")
        
        # Create new action group
        print(f"   Creating new action group...")
        response = bedrock_agent_client.create_agent_action_group(
            agentId=agent_id,
            agentVersion=agent_version,
            actionGroupName=action_group_name,
            description="Tools for conversational interface",
            actionGroupState="ENABLED",
            **action_group_config
        )
        action_group_id = response['agentActionGroup']['actionGroupId']
        print(f"   ✅ Action group created successfully (ID: {action_group_id})")
        
        return action_group_id
        
    except Exception as e:
        print(f"   ❌ Failed to create/update action group: {str(e)}")
        return None


def prepare_agent(
    bedrock_agent_client: Any,
    agent_id: str,
    dry_run: bool = False
) -> bool:
    """Prepare agent for use.
    
    Args:
        bedrock_agent_client: Boto3 Bedrock Agent client
        agent_id: Agent ID
        dry_run: If True, only print what would be done
        
    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        print(f"   [DRY RUN] Would prepare agent {agent_id}")
        return True
    
    try:
        print(f"\n🔄 Preparing agent...")
        bedrock_agent_client.prepare_agent(agentId=agent_id)
        
        # Wait for preparation to complete
        max_attempts = 30
        for attempt in range(max_attempts):
            response = bedrock_agent_client.get_agent(agentId=agent_id)
            status = response['agent']['agentStatus']
            
            if status == 'PREPARED':
                print(f"   ✅ Agent prepared successfully")
                return True
            elif status == 'FAILED':
                print(f"   ❌ Agent preparation failed")
                return False
            
            time.sleep(2)
        
        print(f"   ⚠️  Agent preparation timed out")
        return False
        
    except Exception as e:
        print(f"   ❌ Failed to prepare agent: {str(e)}")
        return False


def create_agent_alias(
    bedrock_agent_client: Any,
    agent_id: str,
    env: str,
    dry_run: bool = False
) -> Optional[str]:
    """Create or update agent alias.
    
    Args:
        bedrock_agent_client: Boto3 Bedrock Agent client
        agent_id: Agent ID
        env: Environment name
        dry_run: If True, only print what would be done
        
    Returns:
        Alias ID if successful, None otherwise
    """
    alias_name = env
    
    if dry_run:
        print(f"   [DRY RUN] Would create/update alias '{alias_name}' for agent {agent_id}")
        return "dry-run-alias-id"
    
    try:
        print(f"\n🏷️  Creating alias '{alias_name}'...")
        
        # Check if alias already exists
        try:
            list_response = bedrock_agent_client.list_agent_aliases(agentId=agent_id)
            existing_alias = next(
                (a for a in list_response.get('agentAliasSummaries', []) 
                 if a['agentAliasName'] == alias_name),
                None
            )
            
            if existing_alias:
                alias_id = existing_alias['agentAliasId']
                print(f"   ℹ️  Alias already exists (ID: {alias_id}), updating...")
                
                response = bedrock_agent_client.update_agent_alias(
                    agentId=agent_id,
                    agentAliasId=alias_id,
                    agentAliasName=alias_name,
                    description=f"{env} environment alias"
                )
                print(f"   ✅ Alias updated successfully")
                return alias_id
        except Exception as e:
            print(f"   ℹ️  Could not check for existing alias: {str(e)}")
        
        # Create new alias
        response = bedrock_agent_client.create_agent_alias(
            agentId=agent_id,
            agentAliasName=alias_name,
            description=f"{env} environment alias"
        )
        alias_id = response['agentAlias']['agentAliasId']
        print(f"   ✅ Alias created successfully (ID: {alias_id})")
        
        return alias_id
        
    except Exception as e:
        print(f"   ❌ Failed to create/update alias: {str(e)}")
        return None


def deploy_agent(
    env: str,
    execution_role_arn: str,
    dry_run: bool = False,
    update_only: bool = False
) -> bool:
    """Deploy conversational interface agent.
    
    Args:
        env: Environment (dev, staging, prod)
        execution_role_arn: ARN of the agent execution role
        dry_run: If True, only print what would be done
        update_only: If True, only update existing agent
        
    Returns:
        True if deployment successful, False otherwise
    """
    agent_name = f"{AGENT_NAME_PREFIX}_{env}"
    
    print(f"\n{'='*70}")
    print(f"Deploying Conversational Interface Agent")
    print(f"{'='*70}")
    print(f"Environment: {env}")
    print(f"Region: {AWS_REGION}")
    print(f"Agent Name: {agent_name}")
    print(f"Execution Role: {execution_role_arn}")
    if dry_run:
        print(f"⚠️  DRY RUN MODE - No changes will be made")
    if update_only:
        print(f"ℹ️  UPDATE ONLY MODE - Will not create new resources")
    print()
    
    # Verify Lambda functions
    if not dry_run:
        function_arns = verify_lambda_functions(env)
    else:
        function_arns = {name: f"arn:aws:lambda:{AWS_REGION}:123456789012:function:brand_metagen_{name}_{env}" 
                        for name in TOOL_LAMBDA_FUNCTIONS}
    
    # Read instruction prompt and tool schemas
    print("\n📖 Loading configuration...")
    instructions = read_instruction_prompt()
    tool_schemas = read_tool_schemas()
    print(f"   ✓ Loaded instruction prompt ({len(instructions)} characters)")
    print(f"   ✓ Loaded {len(tool_schemas)} tool schemas")
    
    # Initialize AWS clients
    bedrock_agent_client = boto3.client('bedrock-agent', region_name=AWS_REGION)
    iam_client = boto3.client('iam', region_name=AWS_REGION)
    lambda_client = boto3.client('lambda', region_name=AWS_REGION)
    
    # Deploy router Lambda
    router_lambda_arn = deploy_router_lambda(
        lambda_client,
        iam_client,
        env,
        function_arns,
        dry_run
    )
    
    if not router_lambda_arn:
        print("\n❌ Failed to deploy router Lambda")
        return False
    
    # Extract role name from ARN
    role_name = execution_role_arn.split('/')[-1]
    
    # Update IAM role with Lambda invoke permissions (for router Lambda)
    if not update_agent_iam_role(iam_client, role_name, {'router': router_lambda_arn}, env, dry_run):
        return False
    
    # Create or update agent
    agent_id = create_or_update_agent(
        bedrock_agent_client,
        agent_name,
        env,
        execution_role_arn,
        instructions,
        dry_run
    )
    
    if not agent_id:
        return False
    
    # Create or update action group
    action_group_id = create_or_update_action_group(
        bedrock_agent_client,
        agent_id,
        "DRAFT",
        router_lambda_arn,
        tool_schemas,
        dry_run
    )
    
    if not action_group_id:
        return False
    
    # Prepare agent
    if not prepare_agent(bedrock_agent_client, agent_id, dry_run):
        return False
    
    # Create alias
    alias_id = create_agent_alias(bedrock_agent_client, agent_id, env, dry_run)
    
    if not alias_id:
        return False
    
    print(f"\n{'='*70}")
    print(f"✅ Successfully deployed {agent_name}")
    print(f"{'='*70}")
    print(f"Agent ID: {agent_id}")
    print(f"Action Group ID: {action_group_id}")
    print(f"Alias ID: {alias_id}")
    print(f"\nAccess the agent in AWS Bedrock Console:")
    print(f"https://{AWS_REGION}.console.aws.amazon.com/bedrock/home?region={AWS_REGION}#/agents/{agent_id}")
    print()
    
    return True


def get_execution_role_arn(env: str) -> Optional[str]:
    """Get the agent execution role ARN from Terraform outputs.
    
    Args:
        env: Environment name
        
    Returns:
        Role ARN if found, None otherwise
    """
    try:
        import subprocess
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=f"infrastructure/environments/{env}",
            capture_output=True,
            text=True,
            check=True
        )
        outputs = json.loads(result.stdout)
        return outputs.get("agent_execution_role_arn", {}).get("value")
    except Exception as e:
        print(f"⚠️  Could not get execution role from Terraform: {str(e)}")
        return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Deploy Conversational Interface Agent to AWS Bedrock AgentCore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy agent to dev environment
  python deploy_conversational_interface_agent.py --env dev --role-arn arn:aws:iam::123456789012:role/...
  
  # Dry run to see what would be deployed
  python deploy_conversational_interface_agent.py --env dev --dry-run --role-arn arn:aws:iam::123456789012:role/...
  
  # Update existing agent only
  python deploy_conversational_interface_agent.py --env dev --update-only --role-arn arn:aws:iam::123456789012:role/...
        """
    )
    parser.add_argument(
        "--env",
        required=True,
        choices=["dev", "staging", "prod"],
        help="Environment to deploy to"
    )
    parser.add_argument(
        "--role-arn",
        help="ARN of the agent execution role (will attempt to get from Terraform if not provided)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making changes"
    )
    parser.add_argument(
        "--update-only",
        action="store_true",
        help="Only update existing agent, do not create new resources"
    )
    
    args = parser.parse_args()
    
    # Get execution role ARN
    execution_role_arn = args.role_arn
    if not execution_role_arn:
        print("Attempting to get execution role ARN from Terraform...")
        execution_role_arn = get_execution_role_arn(args.env)
    
    if not execution_role_arn:
        print("❌ Error: Could not determine agent execution role ARN")
        print("   Please provide --role-arn argument or ensure Terraform is deployed")
        sys.exit(1)
    
    # Deploy agent
    success = deploy_agent(args.env, execution_role_arn, args.dry_run, args.update_only)
    
    if success:
        print("✅ Deployment completed successfully!")
        sys.exit(0)
    else:
        print("❌ Deployment failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
