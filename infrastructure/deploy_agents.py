#!/usr/bin/env python3
"""Deploy all agents to AWS Bedrock AgentCore.

This script deploys Strands-based agents to AWS Bedrock AgentCore runtime.
Each agent is deployed with its handler, tools, and configuration.

Usage:
    python deploy_agents.py --env dev
    python deploy_agents.py --env prod --agent orchestrator
    python deploy_agents.py --env dev --dry-run
"""

import argparse
import json
import sys
import time
import boto3
from pathlib import Path
from typing import List, Optional, Dict, Any


# AWS Configuration
AWS_REGION = "eu-west-1"

# Agent list
AGENTS = [
    "orchestrator",
    "data_transformation",
    "evaluator",
    "metadata_production",
    "commercial_assessment",
    "confirmation",
    "tiebreaker",
]

# Agent configuration
AGENT_CONFIG = {
    "orchestrator": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 600,
        "description": "Coordinates all workflow phases and agent invocations",
    },
    "data_transformation": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 900,
        "description": "Handles data ingestion, validation, and storage operations",
    },
    "evaluator": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 300,
        "description": "Evaluates brand quality and generates production prompts",
    },
    "metadata_production": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 300,
        "description": "Generates regex patterns and MCCID lists for brands",
    },
    "commercial_assessment": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 180,
        "description": "Validates brand existence and sector information",
    },
    "confirmation": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 300,
        "description": "Reviews matched combos to exclude false positives",
    },
    "tiebreaker": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 180,
        "description": "Resolves combos matching multiple brands",
    },
}


def get_agent_instruction_path(agent_name: str) -> Path:
    """Get path to agent instruction file.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        Path to instruction file
    """
    return Path(f"prompts/{agent_name}_instructions.md")


def read_agent_instructions(agent_name: str) -> str:
    """Read agent instructions from file.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        Agent instructions as string
    """
    instruction_path = get_agent_instruction_path(agent_name)
    
    if not instruction_path.exists():
        print(f"⚠️  Warning: Instructions not found at {instruction_path}")
        print(f"   Using default instructions for {agent_name}")
        return f"You are the {agent_name.replace('_', ' ').title()} agent for the Brand Metadata Generator system."
    
    with open(instruction_path, 'r') as f:
        return f.read()


def create_or_update_agent(
    bedrock_agent_client: Any,
    agent_name: str,
    env: str,
    execution_role_arn: str,
    dry_run: bool = False
) -> Optional[str]:
    """Create or update an agent in Bedrock AgentCore.
    
    Args:
        bedrock_agent_client: Boto3 Bedrock Agent client
        agent_name: Name of the agent
        env: Environment (dev, staging, prod)
        execution_role_arn: ARN of the agent execution role
        dry_run: If True, only print what would be done
        
    Returns:
        Agent ID if successful, None otherwise
    """
    config = AGENT_CONFIG.get(agent_name, {})
    full_agent_name = f"brand_metagen_{agent_name}_{env}"
    
    print(f"\n📝 Configuring {full_agent_name}...")
    
    # Read instructions
    instructions = read_agent_instructions(agent_name)
    
    agent_params = {
        "agentName": full_agent_name,
        "agentResourceRoleArn": execution_role_arn,
        "foundationModel": config.get("model", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
        "instruction": instructions,
        "description": config.get("description", f"{agent_name} agent"),
        "idleSessionTTLInSeconds": 1800,  # 30 minutes
    }
    
    if dry_run:
        print(f"   [DRY RUN] Would create/update agent with:")
        print(f"   - Name: {full_agent_name}")
        print(f"   - Model: {agent_params['foundationModel']}")
        print(f"   - Role: {execution_role_arn}")
        return "dry-run-agent-id"
    
    try:
        # Check if agent already exists
        try:
            list_response = bedrock_agent_client.list_agents()
            existing_agent = next(
                (a for a in list_response.get('agentSummaries', []) 
                 if a['agentName'] == full_agent_name),
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
        
        return agent_id
        
    except Exception as e:
        print(f"   ❌ Failed to create/update agent: {str(e)}")
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
        print(f"   Preparing agent...")
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
        print(f"   Creating alias '{alias_name}'...")
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
    agent_name: str,
    env: str,
    execution_role_arn: str,
    dry_run: bool = False
) -> bool:
    """Deploy a single agent to AgentCore.
    
    Args:
        agent_name: Name of the agent to deploy
        env: Environment (dev, staging, prod)
        execution_role_arn: ARN of the agent execution role
        dry_run: If True, only print what would be done
        
    Returns:
        True if deployment successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Deploying {agent_name} agent to {env} environment...")
    print(f"{'='*60}")
    
    # Verify agent directory exists
    agent_path = Path(f"agents/{agent_name}")
    if not agent_path.exists():
        print(f"❌ Error: Agent directory not found: {agent_path}")
        return False
    
    # Initialize Bedrock Agent client
    bedrock_agent_client = boto3.client('bedrock-agent', region_name=AWS_REGION)
    
    # Create or update agent
    agent_id = create_or_update_agent(
        bedrock_agent_client,
        agent_name,
        env,
        execution_role_arn,
        dry_run
    )
    
    if not agent_id:
        return False
    
    # Prepare agent
    if not prepare_agent(bedrock_agent_client, agent_id, dry_run):
        return False
    
    # Create alias
    alias_id = create_agent_alias(bedrock_agent_client, agent_id, env, dry_run)
    
    if not alias_id:
        return False
    
    print(f"\n✅ Successfully deployed brand_metagen_{agent_name}_{env}")
    print(f"   Agent ID: {agent_id}")
    print(f"   Alias ID: {alias_id}")
    
    return True


def deploy_all_agents(
    env: str,
    execution_role_arn: str,
    agents: Optional[List[str]] = None,
    dry_run: bool = False
) -> int:
    """Deploy all or specified agents.
    
    Args:
        env: Environment to deploy to
        execution_role_arn: ARN of the agent execution role
        agents: Optional list of specific agents to deploy
        dry_run: If True, only print what would be done
        
    Returns:
        Number of failed deployments
    """
    agents_to_deploy = agents if agents else AGENTS
    
    print(f"\n🎯 Deploying {len(agents_to_deploy)} agent(s) to {env} environment")
    print(f"Agents: {', '.join(agents_to_deploy)}")
    print(f"Region: {AWS_REGION}")
    print(f"Execution Role: {execution_role_arn}")
    if dry_run:
        print(f"⚠️  DRY RUN MODE - No changes will be made")
    print()
    
    failures = 0
    for agent in agents_to_deploy:
        if agent not in AGENTS:
            print(f"❌ Unknown agent: {agent}")
            failures += 1
            continue
        
        if not deploy_agent(agent, env, execution_role_arn, dry_run):
            failures += 1
    
    print(f"\n{'='*60}")
    print(f"Deployment Summary")
    print(f"{'='*60}")
    print(f"Total agents: {len(agents_to_deploy)}")
    print(f"Successful: {len(agents_to_deploy) - failures}")
    print(f"Failed: {failures}")
    
    return failures


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
            cwd=f"environments/{env}",
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
        description="Deploy agents to AWS Bedrock AgentCore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy all agents to dev
  python deploy_agents.py --env dev --role-arn arn:aws:iam::123456789012:role/brand_metagen_agent_execution_dev
  
  # Deploy specific agent
  python deploy_agents.py --env dev --agent orchestrator --role-arn arn:aws:iam::123456789012:role/...
  
  # Dry run to see what would be deployed
  python deploy_agents.py --env dev --dry-run --role-arn arn:aws:iam::123456789012:role/...
        """
    )
    parser.add_argument(
        "--env",
        required=True,
        choices=["dev", "staging", "prod"],
        help="Environment to deploy to"
    )
    parser.add_argument(
        "--agent",
        help="Specific agent to deploy (default: all agents)"
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
    
    agents = [args.agent] if args.agent else None
    failures = deploy_all_agents(args.env, execution_role_arn, agents, args.dry_run)
    
    if failures > 0:
        print(f"\n❌ Deployment completed with {failures} failure(s)")
        sys.exit(1)
    else:
        print(f"\n✅ All agents deployed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
