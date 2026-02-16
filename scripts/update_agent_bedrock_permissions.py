#!/usr/bin/env python3
"""Update agent execution role with Bedrock model invocation permissions.

This script adds the necessary permissions for the agent to invoke Claude models.
"""

import argparse
import json
import boto3
import sys


def update_role_permissions(role_name: str, region: str = "eu-west-1", account_id: str = None):
    """Update IAM role with Bedrock permissions.
    
    Args:
        role_name: Name of the IAM role to update
        region: AWS region
        account_id: AWS account ID (will be auto-detected if not provided)
    """
    iam_client = boto3.client('iam', region_name=region)
    
    # Get account ID if not provided
    if not account_id:
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
    
    # Policy document for Bedrock model invocation with inference profiles
    # Based on AWS-managed AmazonBedrockAgentInferenceProfilesCrossRegionPolicy
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "BedrockInvokeModel",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:GetInferenceProfile",
                    "bedrock:GetFoundationModel"
                ],
                "Resource": [
                    # Inference profile for Claude 3.7 Sonnet in EU region
                    f"arn:aws:bedrock:{region}:{account_id}:inference-profile/eu.anthropic.claude-3-7-sonnet-20250219-v1:0",
                    # Cross-region foundation model access
                    f"arn:aws:bedrock:*::foundation-model/anthropic.claude-3-7-sonnet-20250219-v1:0",
                    # Fallback for other Claude models
                    f"arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
                ]
            }
        ]
    }
    
    policy_name = "BedrockModelInvocation"
    
    try:
        # Add inline policy to role
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print(f"✅ Successfully added Bedrock permissions to role: {role_name}")
        print(f"   Policy: {policy_name}")
        print(f"   Actions: InvokeModel, InvokeModelWithResponseStream, GetInferenceProfile, GetFoundationModel")
        print(f"   Inference Profile: eu.anthropic.claude-3-7-sonnet-20250219-v1:0")
        print(f"   Foundation Models: Claude 3.7 Sonnet and other Claude models")
        return True
        
    except iam_client.exceptions.NoSuchEntityException:
        print(f"❌ Error: Role not found: {role_name}")
        return False
    except Exception as e:
        print(f"❌ Error updating role permissions: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Update agent execution role with Bedrock permissions"
    )
    parser.add_argument(
        "--role-name",
        required=True,
        help="Name of the IAM role to update (e.g., brand_metagen_agent_execution_dev)"
    )
    parser.add_argument(
        "--region",
        default="eu-west-1",
        help="AWS region (default: eu-west-1)"
    )
    parser.add_argument(
        "--account-id",
        help="AWS account ID (will be auto-detected if not provided)"
    )
    
    args = parser.parse_args()
    
    print(f"\n{'='*70}")
    print(f"Updating IAM Role Bedrock Permissions")
    print(f"{'='*70}")
    print(f"Role: {args.role_name}")
    print(f"Region: {args.region}")
    print()
    
    success = update_role_permissions(args.role_name, args.region, args.account_id)
    
    if success:
        print("\n✅ Permissions updated successfully!")
        print("   The agent can now invoke Claude models in Bedrock.")
        sys.exit(0)
    else:
        print("\n❌ Failed to update permissions")
        sys.exit(1)


if __name__ == "__main__":
    main()
