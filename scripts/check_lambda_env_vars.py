#!/usr/bin/env python3
"""Check Lambda function environment variables."""

import argparse
import json
import boto3
import sys


def check_env_vars(function_name: str, region: str = "eu-west-1"):
    """Check environment variables for a Lambda function.
    
    Args:
        function_name: Lambda function name
        region: AWS region
    """
    lambda_client = boto3.client('lambda', region_name=region)
    
    try:
        print(f"\n{'='*70}")
        print(f"Lambda Function Environment Variables")
        print(f"{'='*70}")
        print(f"Function: {function_name}")
        print(f"Region: {region}")
        print(f"{'='*70}\n")
        
        # Get function configuration
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        
        print(f"Runtime: {response.get('Runtime', 'N/A')}")
        print(f"Handler: {response.get('Handler', 'N/A')}")
        print(f"Timeout: {response.get('Timeout', 'N/A')} seconds")
        print(f"Memory: {response.get('MemorySize', 'N/A')} MB")
        print(f"Last Modified: {response.get('LastModified', 'N/A')}")
        print()
        
        # Get environment variables
        env_vars = response.get('Environment', {}).get('Variables', {})
        
        if env_vars:
            print(f"Environment Variables ({len(env_vars)}):")
            print(f"{'-'*70}")
            for key, value in sorted(env_vars.items()):
                # Mask sensitive values
                if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key', 'token']):
                    display_value = '***MASKED***'
                else:
                    display_value = value
                print(f"  {key} = {display_value}")
        else:
            print("⚠️  No environment variables set")
        
        print(f"\n{'='*70}\n")
        
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
        description="Check Lambda function environment variables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python check_lambda_env_vars.py --function brand_metagen_start_workflow_dev
        """
    )
    parser.add_argument(
        "--function",
        required=True,
        help="Lambda function name"
    )
    parser.add_argument(
        "--region",
        default="eu-west-1",
        help="AWS region (default: eu-west-1)"
    )
    
    args = parser.parse_args()
    
    success = check_env_vars(args.function, args.region)
    
    if success:
        sys.exit(0)
    else:
        print("\n❌ Failed to check environment variables")
        sys.exit(1)


if __name__ == "__main__":
    main()
