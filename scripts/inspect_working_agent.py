#!/usr/bin/env python3
"""Inspect a working Bedrock Agent to see its exact model configuration.

This script retrieves the configuration of a working agent to identify
the exact model identifier format being used.
"""

import argparse
import json
import boto3
import sys


def inspect_agent(agent_id: str, region: str = "eu-west-1"):
    """Inspect agent configuration.
    
    Args:
        agent_id: Agent ID to inspect
        region: AWS region
    """
    bedrock_agent_client = boto3.client('bedrock-agent', region_name=region)
    
    try:
        # Get agent details
        print(f"\n{'='*70}")
        print(f"Inspecting Agent Configuration")
        print(f"{'='*70}")
        print(f"Agent ID: {agent_id}")
        print(f"Region: {region}")
        print()
        
        response = bedrock_agent_client.get_agent(agentId=agent_id)
        agent = response['agent']
        
        print(f"Agent Name: {agent['agentName']}")
        print(f"Agent Status: {agent['agentStatus']}")
        print(f"\n🔑 FOUNDATION MODEL CONFIGURATION:")
        print(f"   Model ID: {agent.get('foundationModel', 'NOT SET')}")
        print(f"\nAgent Description: {agent.get('description', 'N/A')}")
        print(f"Idle Session TTL: {agent.get('idleSessionTTLInSeconds', 'N/A')} seconds")
        print(f"Execution Role ARN: {agent.get('agentResourceRoleArn', 'N/A')}")
        
        # Get agent aliases
        print(f"\n📋 Agent Aliases:")
        try:
            aliases_response = bedrock_agent_client.list_agent_aliases(agentId=agent_id)
            for alias in aliases_response.get('agentAliasSummaries', []):
                print(f"   - {alias['agentAliasName']} (ID: {alias['agentAliasId']})")
        except Exception as e:
            print(f"   Could not list aliases: {str(e)}")
        
        # Get action groups
        print(f"\n🔧 Action Groups:")
        try:
            action_groups_response = bedrock_agent_client.list_agent_action_groups(
                agentId=agent_id,
                agentVersion='DRAFT'
            )
            for ag in action_groups_response.get('actionGroupSummaries', []):
                print(f"   - {ag['actionGroupName']} (ID: {ag['actionGroupId']}, State: {ag['actionGroupState']})")
        except Exception as e:
            print(f"   Could not list action groups: {str(e)}")
        
        # Print full JSON for reference
        print(f"\n📄 Full Agent Configuration (JSON):")
        print(json.dumps(agent, indent=2, default=str))
        
        return True
        
    except bedrock_agent_client.exceptions.ResourceNotFoundException:
        print(f"❌ Error: Agent not found: {agent_id}")
        return False
    except Exception as e:
        print(f"❌ Error inspecting agent: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def list_agents(region: str = "eu-west-1"):
    """List all agents in the region.
    
    Args:
        region: AWS region
    """
    bedrock_agent_client = boto3.client('bedrock-agent', region_name=region)
    
    try:
        print(f"\n{'='*70}")
        print(f"Listing All Agents")
        print(f"{'='*70}")
        print(f"Region: {region}")
        print()
        
        response = bedrock_agent_client.list_agents()
        agents = response.get('agentSummaries', [])
        
        if not agents:
            print("No agents found in this region.")
            return True
        
        print(f"Found {len(agents)} agent(s):\n")
        for agent in agents:
            print(f"Name: {agent['agentName']}")
            print(f"  ID: {agent['agentId']}")
            print(f"  Status: {agent['agentStatus']}")
            print(f"  Updated: {agent.get('updatedAt', 'N/A')}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error listing agents: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Inspect Bedrock Agent configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all agents
  python inspect_working_agent.py --list
  
  # Inspect specific agent
  python inspect_working_agent.py --agent-id GZF9REHEAO
  
  # Inspect agent in different region
  python inspect_working_agent.py --agent-id GZF9REHEAO --region us-east-1
        """
    )
    parser.add_argument(
        "--agent-id",
        help="Agent ID to inspect"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all agents in the region"
    )
    parser.add_argument(
        "--region",
        default="eu-west-1",
        help="AWS region (default: eu-west-1)"
    )
    
    args = parser.parse_args()
    
    if args.list:
        success = list_agents(args.region)
    elif args.agent_id:
        success = inspect_agent(args.agent_id, args.region)
    else:
        parser.print_help()
        print("\n❌ Error: Must provide either --agent-id or --list")
        sys.exit(1)
    
    if success:
        print("\n✅ Inspection completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Inspection failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
