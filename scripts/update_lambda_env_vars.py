#!/usr/bin/env python3
"""Update Lambda function environment variables."""

import argparse
import json
import boto3
import sys


def update_env_vars(function_name: str, env_vars: dict, region: str = "eu-west-1"):
    """Update environment variables for a Lambda function.
    
    Args:
        function_name: Lambda function name
        env_vars: Dictionary of environment variables to add/update
        region: AWS region
    """
    lambda_client = boto3.client('lambda', region_name=region)
    
    try:
        print(f"\n{'='*70}")
        print(f"Updating Lambda Function Environment Variables")
        print(f"{'='*70}")
        print(f"Function: {function_name}")
        print(f"Region: {region}")
        print(f"{'='*70}\n")
        
        # Get current configuration
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        
        # Get existing environment variables
        current_env = response.get('Environment', {}).get('Variables', {})
        
        print(f"Current environment variables: {len(current_env)}")
        for key, value in sorted(current_env.items()):
            print(f"  {key} = {value}")
        
        # Merge with new variables
        updated_env = {**current_env, **env_vars}
        
        print(f"\nNew/Updated variables:")
        for key, value in env_vars.items():
            if key in current_env:
                print(f"  {key} = {value} (UPDATED)")
            else:
                print(f"  {key} = {value} (NEW)")
        
        # Update function configuration
        print(f"\nUpdating Lambda function...")
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': updated_env}
        )
        
        print(f"✅ Successfully updated environment variables")
        print(f"\nTotal environment variables: {len(updated_env)}")
        
        return True
        
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"❌ Lambda function not found: {function_name}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Update Lambda function environment variables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add STATE_MACHINE_ARN
  python update_lambda_env_vars.py --function brand_metagen_start_workflow_dev --env STATE_MACHINE_ARN=arn:aws:states:...
  
  # Add multiple variables
  python update_lambda_env_vars.py --function my-function --env VAR1=value1 --env VAR2=value2
        """
    )
    parser.add_argument(
        "--function",
        required=True,
        help="Lambda function name"
    )
    parser.add_argument(
        "--env",
        action='append',
        required=True,
        help="Environment variable in KEY=VALUE format (can be specified multiple times)"
    )
    parser.add_argument(
        "--region",
        default="eu-west-1",
        help="AWS region (default: eu-west-1)"
    )
    
    args = parser.parse_args()
    
    # Parse environment variables
    env_vars = {}
    for env_str in args.env:
        if '=' not in env_str:
            print(f"❌ Invalid format: {env_str}")
            print("   Expected format: KEY=VALUE")
            sys.exit(1)
        
        key, value = env_str.split('=', 1)
        env_vars[key] = value
    
    success = update_env_vars(args.function, env_vars, args.region)
    
    if success:
        print("\n✅ Environment variables updated successfully!")
        sys.exit(0)
    else:
        print("\n❌ Failed to update environment variables")
        sys.exit(1)


if __name__ == "__main__":
    main()
