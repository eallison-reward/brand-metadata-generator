#!/usr/bin/env python3
"""Deploy workflow Lambda functions for Step Functions workflow.

This script packages and deploys the Lambda functions required
by the brand_metagen_workflow Step Functions state machine.
"""

import boto3
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

AWS_REGION = "eu-west-1"
PYTHON_RUNTIME = "python3.12"
TIMEOUT = 300
MEMORY_SIZE = 512

# Lambda function configurations
LAMBDA_FUNCTIONS = [
    {
        "name": "workflow_init",
        "handler": "handler.lambda_handler",
        "description": "Initialize workflow configuration and validate inputs",
        "timeout": 60,
    },
    {
        "name": "orchestrator_invoke",
        "handler": "handler.lambda_handler",
        "description": "Invoke Orchestrator Agent to coordinate workflow phases",
        "timeout": 900,  # Maximum Lambda timeout is 15 minutes
        "memory": 1024,
    },
    {
        "name": "result_aggregation",
        "handler": "handler.lambda_handler",
        "description": "Aggregate results from all processed brands",
        "timeout": 300,
    },
]

# Environment variables for all functions
ENV_VARS = {
    "S3_BUCKET": "brand-generator-rwrd-023-eu-west-1",
    "ATHENA_DATABASE": "brand_metadata_generator_db",
    "ORCHESTRATOR_AGENT_ID": "brand_metagen_orchestrator-VVTBH860nM",
}


def create_deployment_package(function_name, temp_dir):
    """Create deployment package for a Lambda function.
    
    Args:
        function_name: Name of the function
        temp_dir: Temporary directory for packaging
        
    Returns:
        Path to the ZIP file
    """
    print(f"   📦 Creating deployment package...")
    
    package_dir = Path(temp_dir) / "package"
    package_dir.mkdir(exist_ok=True)
    
    # Copy Lambda function code
    function_dir = Path("lambda_functions") / function_name
    if function_dir.exists():
        for file in function_dir.glob("*.py"):
            shutil.copy(file, package_dir / file.name)
            print(f"      Added {file.name}")
    else:
        print(f"   ❌ Function directory not found: {function_dir}")
        return None
    
    # Copy shared utilities if they exist
    shared_dir = Path("shared")
    if shared_dir.exists():
        shutil.copytree(shared_dir, package_dir / "shared", dirs_exist_ok=True)
        print(f"      Added shared utilities")
    
    # Create ZIP file
    zip_path = Path(temp_dir) / f"{function_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            # Skip __pycache__ and .pyc files
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if not file.endswith(".pyc"):
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(package_dir)
                    zipf.write(file_path, arcname)
    
    print(f"   ✅ Package created: {zip_path.name} ({zip_path.stat().st_size / 1024:.1f} KB)")
    return zip_path


def get_or_create_execution_role(iam_client, env):
    """Get or create IAM execution role for Lambda functions.
    
    Args:
        iam_client: Boto3 IAM client
        env: Environment name
        
    Returns:
        Role ARN
    """
    role_name = f"brand_metagen_workflow_lambdas_{env}"
    
    try:
        # Try to get existing role
        response = iam_client.get_role(RoleName=role_name)
        role_arn = response["Role"]["Arn"]
        print(f"   ✅ Using existing role: {role_arn}")
        return role_arn
    except iam_client.exceptions.NoSuchEntityException:
        pass
    
    # Create new role
    print(f"   Creating IAM role: {role_name}...")
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    
    response = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description=f"Execution role for workflow Lambda functions ({env})",
    )
    role_arn = response["Role"]["Arn"]
    
    # Attach basic Lambda execution policy
    iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )
    
    # Create and attach custom policy for workflow functions
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket",
                ],
                "Resource": [
                    f"arn:aws:s3:::brand-generator-rwrd-023-eu-west-1",
                    f"arn:aws:s3:::brand-generator-rwrd-023-eu-west-1/*",
                ],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "athena:StartQueryExecution",
                    "athena:GetQueryExecution",
                    "athena:GetQueryResults",
                ],
                "Resource": "*",
            },
            {
                "Effect": "Allow",
                "Action": [
                    "glue:GetDatabase",
                    "glue:GetTable",
                ],
                "Resource": "*",
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeAgent",
                ],
                "Resource": "*",
            },
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                ],
                "Resource": "*",
            },
        ],
    }
    
    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName="workflow_lambdas_policy",
        PolicyDocument=json.dumps(policy_document),
    )
    
    print(f"   ✅ Created role: {role_arn}")
    print(f"   ⏳ Waiting 10 seconds for IAM propagation...")
    import time
    time.sleep(10)
    
    return role_arn


def deploy_lambda_function(lambda_client, function_config, zip_path, role_arn, env):
    """Deploy a Lambda function.
    
    Args:
        lambda_client: Boto3 Lambda client
        function_config: Function configuration dictionary
        zip_path: Path to deployment ZIP
        role_arn: IAM role ARN
        env: Environment name
        
    Returns:
        True if successful, False otherwise
    """
    function_name = f"brand_metagen_{function_config['name']}_{env}"
    
    print(f"\n📝 Deploying {function_name}...")
    
    # Read ZIP file
    with open(zip_path, "rb") as f:
        zip_content = f.read()
    
    timeout = function_config.get("timeout", TIMEOUT)
    memory = function_config.get("memory", MEMORY_SIZE)
    
    try:
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName=function_name)
            print(f"   ℹ️  Function exists, updating code...")
            
            # Update function code
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content,
            )
            
            # Wait for update to complete
            print(f"   ⏳ Waiting for code update to complete...")
            waiter = lambda_client.get_waiter('function_updated')
            waiter.wait(FunctionName=function_name)
            
            # Update function configuration
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                Runtime=PYTHON_RUNTIME,
                Handler=function_config["handler"],
                Timeout=timeout,
                MemorySize=memory,
                Environment={"Variables": ENV_VARS},
            )
            
            print(f"   ✅ Function updated successfully")
            return True
            
        except lambda_client.exceptions.ResourceNotFoundException:
            # Create new function
            print(f"   Creating new function...")
            
            lambda_client.create_function(
                FunctionName=function_name,
                Runtime=PYTHON_RUNTIME,
                Role=role_arn,
                Handler=function_config["handler"],
                Code={"ZipFile": zip_content},
                Description=function_config["description"],
                Timeout=timeout,
                MemorySize=memory,
                Environment={"Variables": ENV_VARS},
            )
            
            print(f"   ✅ Function created successfully")
            return True
            
    except Exception as e:
        print(f"   ❌ Failed to deploy function: {str(e)}")
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy workflow Lambda functions")
    parser.add_argument("--env", required=True, choices=["dev", "prod"], help="Environment")
    parser.add_argument("--function", help="Deploy specific function only")
    args = parser.parse_args()
    
    print(f"\n{'='*70}")
    print(f"Deploying Workflow Lambda Functions")
    print(f"{'='*70}")
    print(f"Environment: {args.env}")
    print(f"Region: {AWS_REGION}")
    print()
    
    # Initialize AWS clients
    lambda_client = boto3.client("lambda", region_name=AWS_REGION)
    iam_client = boto3.client("iam", region_name=AWS_REGION)
    
    # Get or create execution role
    print("🔐 Setting up IAM role...")
    role_arn = get_or_create_execution_role(iam_client, args.env)
    print()
    
    # Filter functions if specific function requested
    functions_to_deploy = LAMBDA_FUNCTIONS
    if args.function:
        functions_to_deploy = [f for f in LAMBDA_FUNCTIONS if f["name"] == args.function]
        if not functions_to_deploy:
            print(f"❌ Function '{args.function}' not found")
            sys.exit(1)
    
    # Deploy each function
    success_count = 0
    with tempfile.TemporaryDirectory() as temp_dir:
        for function_config in functions_to_deploy:
            # Create deployment package
            zip_path = create_deployment_package(function_config["name"], temp_dir)
            if not zip_path:
                continue
            
            # Deploy function
            if deploy_lambda_function(lambda_client, function_config, zip_path, role_arn, args.env):
                success_count += 1
    
    # Summary
    print(f"\n{'='*70}")
    if success_count == len(functions_to_deploy):
        print(f"✅ Successfully deployed all {len(functions_to_deploy)} functions")
    else:
        print(f"⚠️  Deployed {success_count}/{len(functions_to_deploy)} functions")
    print(f"{'='*70}\n")
    
    sys.exit(0 if success_count == len(functions_to_deploy) else 1)


if __name__ == "__main__":
    main()
