#!/usr/bin/env python3
"""Check IAM role permissions for Bedrock Agent.

This script inspects the IAM role attached to an agent to verify
it has the necessary permissions for Bedrock model invocation.
"""

import argparse
import json
import boto3
import sys


def check_role_permissions(role_name: str, region: str = "eu-west-1"):
    """Check IAM role permissions.
    
    Args:
        role_name: Name of the IAM role
        region: AWS region
    """
    iam_client = boto3.client('iam')
    
    try:
        print(f"\n{'='*70}")
        print(f"Checking IAM Role Permissions")
        print(f"{'='*70}")
        print(f"Role: {role_name}")
        print(f"Region: {region}")
        print()
        
        # Get role details
        role_response = iam_client.get_role(RoleName=role_name)
        role = role_response['Role']
        
        print(f"Role ARN: {role['Arn']}")
        print(f"Created: {role['CreateDate']}")
        print()
        
        # Get attached managed policies
        print(f"📋 Attached Managed Policies:")
        attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
        if attached_policies['AttachedPolicies']:
            for policy in attached_policies['AttachedPolicies']:
                print(f"   - {policy['PolicyName']}")
                print(f"     ARN: {policy['PolicyArn']}")
        else:
            print(f"   (none)")
        print()
        
        # Get inline policies
        print(f"📄 Inline Policies:")
        inline_policies = iam_client.list_role_policies(RoleName=role_name)
        if inline_policies['PolicyNames']:
            for policy_name in inline_policies['PolicyNames']:
                print(f"\n   Policy: {policy_name}")
                policy_response = iam_client.get_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )
                policy_doc = policy_response['PolicyDocument']
                print(f"   Document:")
                print(json.dumps(policy_doc, indent=6))
        else:
            print(f"   (none)")
        print()
        
        # Check for Bedrock permissions
        print(f"🔍 Checking for Bedrock Permissions:")
        has_bedrock_invoke = False
        
        # Check inline policies
        for policy_name in inline_policies['PolicyNames']:
            policy_response = iam_client.get_role_policy(
                RoleName=role_name,
                PolicyName=policy_name
            )
            policy_doc = policy_response['PolicyDocument']
            
            for statement in policy_doc.get('Statement', []):
                actions = statement.get('Action', [])
                if isinstance(actions, str):
                    actions = [actions]
                
                for action in actions:
                    if 'bedrock:InvokeModel' in action or action == 'bedrock:*':
                        has_bedrock_invoke = True
                        print(f"   ✅ Found Bedrock invoke permission in inline policy '{policy_name}'")
                        print(f"      Action: {action}")
                        print(f"      Resources: {statement.get('Resource', 'N/A')}")
        
        # Check managed policies (basic check - would need to get policy versions for full check)
        for policy in attached_policies['AttachedPolicies']:
            if 'Bedrock' in policy['PolicyName']:
                print(f"   ℹ️  Found Bedrock-related managed policy: {policy['PolicyName']}")
        
        if not has_bedrock_invoke:
            print(f"   ⚠️  No explicit Bedrock InvokeModel permission found in inline policies")
            print(f"      (May be in managed policies - check AWS Console for details)")
        
        print()
        
        # Get trust policy
        print(f"🔐 Trust Policy (AssumeRole):")
        trust_policy = role['AssumeRolePolicyDocument']
        print(json.dumps(trust_policy, indent=3))
        print()
        
        return True
        
    except iam_client.exceptions.NoSuchEntityException:
        print(f"❌ Error: Role not found: {role_name}")
        return False
    except Exception as e:
        print(f"❌ Error checking role: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def check_agent_role(agent_id: str, region: str = "eu-west-1"):
    """Check the IAM role for a specific agent.
    
    Args:
        agent_id: Agent ID
        region: AWS region
    """
    bedrock_agent_client = boto3.client('bedrock-agent', region_name=region)
    
    try:
        # Get agent details
        response = bedrock_agent_client.get_agent(agentId=agent_id)
        agent = response['agent']
        
        role_arn = agent.get('agentResourceRoleArn')
        if not role_arn:
            print(f"❌ Error: Agent has no execution role ARN")
            return False
        
        # Extract role name from ARN
        role_name = role_arn.split('/')[-1]
        
        print(f"Agent: {agent['agentName']} (ID: {agent_id})")
        print(f"Execution Role ARN: {role_arn}")
        print(f"Execution Role Name: {role_name}")
        
        return check_role_permissions(role_name, region)
        
    except bedrock_agent_client.exceptions.ResourceNotFoundException:
        print(f"❌ Error: Agent not found: {agent_id}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Check IAM role permissions for Bedrock Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check role by name
  python check_agent_permissions.py --role-name brand_metagen_agent_execution_dev
  
  # Check role for specific agent
  python check_agent_permissions.py --agent-id GZF9REHEAO
        """
    )
    parser.add_argument(
        "--role-name",
        help="Name of the IAM role to check"
    )
    parser.add_argument(
        "--agent-id",
        help="Agent ID (will look up its execution role)"
    )
    parser.add_argument(
        "--region",
        default="eu-west-1",
        help="AWS region (default: eu-west-1)"
    )
    
    args = parser.parse_args()
    
    if args.agent_id:
        success = check_agent_role(args.agent_id, args.region)
    elif args.role_name:
        success = check_role_permissions(args.role_name, args.region)
    else:
        parser.print_help()
        print("\n❌ Error: Must provide either --role-name or --agent-id")
        sys.exit(1)
    
    if success:
        print("\n✅ Check completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Check failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
