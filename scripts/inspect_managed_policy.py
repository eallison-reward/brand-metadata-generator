#!/usr/bin/env python3
"""Inspect managed IAM policy to see its permissions."""

import argparse
import json
import boto3
import sys


def inspect_managed_policy(policy_arn: str):
    """Inspect a managed policy.
    
    Args:
        policy_arn: ARN of the policy to inspect
    """
    iam_client = boto3.client('iam')
    
    try:
        print(f"\n{'='*70}")
        print(f"Inspecting Managed Policy")
        print(f"{'='*70}")
        print(f"Policy ARN: {policy_arn}")
        print()
        
        # Get policy details
        policy_response = iam_client.get_policy(PolicyArn=policy_arn)
        policy = policy_response['Policy']
        
        print(f"Policy Name: {policy['PolicyName']}")
        print(f"Description: {policy.get('Description', 'N/A')}")
        print(f"Created: {policy['CreateDate']}")
        print(f"Updated: {policy['UpdateDate']}")
        print(f"Default Version: {policy['DefaultVersionId']}")
        print()
        
        # Get policy version (the actual permissions)
        version_response = iam_client.get_policy_version(
            PolicyArn=policy_arn,
            VersionId=policy['DefaultVersionId']
        )
        
        policy_document = version_response['PolicyVersion']['Document']
        
        print(f"📄 Policy Document:")
        print(json.dumps(policy_document, indent=2))
        print()
        
        return True
        
    except iam_client.exceptions.NoSuchEntityException:
        print(f"❌ Error: Policy not found: {policy_arn}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Inspect managed IAM policy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python inspect_managed_policy.py --policy-arn arn:aws:iam::123456789012:policy/MyPolicy
        """
    )
    parser.add_argument(
        "--policy-arn",
        required=True,
        help="ARN of the managed policy to inspect"
    )
    
    args = parser.parse_args()
    
    success = inspect_managed_policy(args.policy_arn)
    
    if success:
        print("✅ Inspection completed successfully!")
        sys.exit(0)
    else:
        print("❌ Inspection failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
