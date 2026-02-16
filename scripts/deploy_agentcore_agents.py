#!/usr/bin/env python3
"""Deploy workflow agents to AWS Bedrock AgentCore using Strands API.

This script deploys Strands-based agents to AWS Bedrock AgentCore runtime
using the AgentCore CLI. These agents handle the core workflow processing.

The Conversational Interface Agent is deployed separately to Bedrock Agents
as it needs to interface with users through natural language.

IMPORTANT - AgentCore CLI Location:
On Windows, the AgentCore CLI is typically installed at:
- User install: C:\\Users\\{username}\\AppData\\Roaming\\Python\\Python314\\Scripts\\agentcore.exe
- System install: C:\\Python314\\Scripts\\agentcore.exe

The CLI does NOT support --version flag. Use --help instead.
Available commands: create, dev, deploy, invoke, status, destroy, stop-session, etc.

Usage:
    python deploy_agentcore_agents.py --env dev
    python deploy_agentcore_agents.py --env prod --agent orchestrator
    python deploy_agentcore_agents.py --env dev --dry-run
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Dict, Any


# AWS Configuration
AWS_REGION = "eu-west-1"

# AgentCore workflow agents (NOT the conversational interface agent)
AGENTCORE_AGENTS = [
    "orchestrator",
    "data_transformation", 
    "evaluator",
    "metadata_production",
    "commercial_assessment",
    "confirmation",
    "tiebreaker",
    "feedback_processing",
    "learning_analytics",
]

# Agent configuration for AgentCore
AGENT_CONFIG = {
    "orchestrator": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 600,
        "description": "Coordinates all workflow phases and agent invocations",
        "memory_size": 512,
    },
    "data_transformation": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0", 
        "timeout": 900,
        "description": "Handles data ingestion, validation, and storage operations",
        "memory_size": 512,
    },
    "evaluator": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 300,
        "description": "Evaluates brand quality and generates production prompts",
        "memory_size": 256,
    },
    "metadata_production": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 300,
        "description": "Generates regex patterns and MCCID lists for brands",
        "memory_size": 256,
    },
    "commercial_assessment": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 180,
        "description": "Validates brand existence and sector information",
        "memory_size": 256,
    },
    "confirmation": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 300,
        "description": "Reviews matched combos to exclude false positives",
        "memory_size": 256,
    },
    "tiebreaker": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 180,
        "description": "Resolves combos matching multiple brands",
        "memory_size": 256,
    },
    "feedback_processing": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 300,
        "description": "Processes human feedback and generates refinement prompts",
        "memory_size": 256,
    },
    "learning_analytics": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 300,
        "description": "Analyzes feedback trends and calculates accuracy metrics",
        "memory_size": 256,
    },
}


def check_agentcore_cli() -> bool:
    """Check if AgentCore CLI is installed and configured.
    
    Returns:
        True if CLI is available, False otherwise
    """
    # Try different possible paths for agentcore CLI
    possible_paths = [
        "agentcore",  # If in PATH
        r"C:\Users\eda\AppData\Roaming\Python\Python314\Scripts\agentcore.exe",  # User Scripts
        r"C:\Python314\Scripts\agentcore.exe",  # System Scripts
    ]
    
    for agentcore_path in possible_paths:
        try:
            result = subprocess.run(
                [agentcore_path, "--help"],
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8',
                errors='replace'
            )
            if result.stdout and "BedrockAgentCore CLI" in result.stdout:
                print(f"✅ AgentCore CLI found at: {agentcore_path}")
                # Store the working path globally
                globals()['AGENTCORE_PATH'] = agentcore_path
                return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    print("❌ AgentCore CLI not found")
    print("   Install with: pip install bedrock-agentcore-starter-toolkit")
    print("   Expected locations:")
    print("   - User: C:\\\\Users\\\\{username}\\\\AppData\\\\Roaming\\\\Python\\\\Python314\\\\Scripts\\\\agentcore.exe")
    print("   - System: C:\\\\Python314\\\\Scripts\\\\agentcore.exe")
    return False


def deploy_agent_to_agentcore(
    agent_name: str,
    env: str,
    dry_run: bool = False
) -> bool:
    """Deploy a single agent to AgentCore using the CLI.
    
    Args:
        agent_name: Name of the agent to deploy
        env: Environment (dev, staging, prod)
        dry_run: If True, only print what would be done
        
    Returns:
        True if deployment successful, False otherwise
    """
    print(f"\n📝 Deploying {agent_name} to AgentCore...")
    
    try:
        # Path to agent handler
        handler_path = Path(f"agents/{agent_name}/agentcore_handler.py")
        
        if not handler_path.exists():
            print(f"   ❌ Agent handler not found: {handler_path}")
            return False
        
        if dry_run:
            print(f"   [DRY RUN] Would deploy agent:")
            print(f"   - Agent: {agent_name}")
            print(f"   - Handler: {handler_path}")
            print(f"   - Environment: {env}")
            return True
        
        # Use agentcore deploy command with the agent name
        # The CLI will use the configuration from .bedrock_agentcore.yaml
        full_agent_name = f"brand_metagen_{agent_name}"
        command = [
            globals().get('AGENTCORE_PATH', 'agentcore'),
            "deploy",
            "--agent", full_agent_name,
            "--auto-update-on-conflict"  # Automatically update existing agent
        ]
        
        # Add local flag if specified in environment variable
        if os.environ.get('AGENTCORE_LOCAL_DEPLOY') == 'true':
            command.append("--local")
        
        print(f"   Executing: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=".",  # Run from project root where .bedrock_agentcore.yaml is located
            encoding='utf-8',
            errors='replace',
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        
        # Check for error indicators in output even if exit code is 0
        if result.stderr:
            stderr_lower = result.stderr.lower()
            # Only fail on actual errors, not warnings
            if ("error" in stderr_lower or "failed" in stderr_lower or "exception" in stderr_lower):
                # Check if it's just a warning about observability traces (not a deployment failure)
                if "traces delivery setup warning" in stderr_lower or "failed to enable observability" in stderr_lower:
                    # This is just a warning, not a deployment failure - continue
                    pass
                else:
                    print(f"   ❌ Deployment failed with errors in stderr")
                    print(f"   Error: {result.stderr.strip()}")
                    return False
        
        # Check for CodeBuild failures in stdout
        if result.stdout:
            stdout_content = result.stdout
            # Check for CodeBuild failure patterns
            if "BUILD_FAILED" in stdout_content or ("COMPLETED" in stdout_content and "FAILED" in stdout_content):
                print(f"   ❌ CodeBuild container build failed")
                print(f"   Output: {stdout_content.strip()}")
                return False
            # Check for other failure indicators
            if "deployment failed" in stdout_content.lower() or "error:" in stdout_content.lower():
                print(f"   ❌ Deployment failed")
                print(f"   Output: {stdout_content.strip()}")
                return False
        
        print(f"   ✅ Agent deployed successfully")
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Deployment failed: {e}")
        if e.stderr:
            print(f"   Error: {e.stderr.strip()}")
        if e.stdout:
            print(f"   Output: {e.stdout.strip()}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False


def deploy_all_agents(
    env: str,
    agents: Optional[List[str]] = None,
    dry_run: bool = False
) -> int:
    """Deploy all or specified agents to AgentCore.
    
    Args:
        env: Environment to deploy to
        agents: Optional list of specific agents to deploy
        dry_run: If True, only print what would be done
        
    Returns:
        Number of failed deployments
    """
    agents_to_deploy = agents if agents else AGENTCORE_AGENTS
    
    print(f"\n🎯 Deploying {len(agents_to_deploy)} agent(s) to AgentCore")
    print(f"Environment: {env}")
    print(f"Region: {AWS_REGION}")
    print(f"Agents: {', '.join(agents_to_deploy)}")
    if dry_run:
        print(f"⚠️  DRY RUN MODE - No changes will be made")
    print()
    
    # Check if AgentCore configuration exists
    config_path = Path(".bedrock_agentcore.yaml")
    if not config_path.exists():
        print("📝 AgentCore configuration not found. Creating configuration...")
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "scripts/configure_agentcore.py"],
                check=True,
                capture_output=True,
                text=True
            )
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create AgentCore configuration: {e}")
            if e.stdout:
                print(f"Output: {e.stdout}")
            if e.stderr:
                print(f"Error: {e.stderr}")
            return len(agents_to_deploy)
    
    failures = 0
    for agent in agents_to_deploy:
        if agent not in AGENTCORE_AGENTS:
            print(f"❌ Unknown agent: {agent}")
            print(f"   Available agents: {', '.join(AGENTCORE_AGENTS)}")
            failures += 1
            continue
        
        if not deploy_agent_to_agentcore(agent, env, dry_run):
            failures += 1
    
    print(f"\n{'='*60}")
    print(f"AgentCore Deployment Summary")
    print(f"{'='*60}")
    print(f"Total agents: {len(agents_to_deploy)}")
    print(f"Successful: {len(agents_to_deploy) - failures}")
    print(f"Failed: {failures}")
    
    if failures == 0:
        print(f"\n✅ All agents deployed successfully to AgentCore!")
        print(f"\nNext steps:")
        print(f"1. Deploy Conversational Interface Agent to Bedrock Agents:")
        print(f"   python scripts/deploy_conversational_interface_agent.py --env {env}")
        print(f"2. Test agent connectivity:")
        print(f"   agentcore status")
    else:
        print(f"\n❌ {failures} agent(s) failed to deploy")
    
    return failures


def list_deployed_agents(env: str) -> None:
    """List all deployed agents in AgentCore.
    
    Args:
        env: Environment to check
    """
    print(f"\n📋 Listing deployed agents for {env} environment...")
    
    try:
        result = subprocess.run(
            [globals().get('AGENTCORE_PATH', 'agentcore'), "status"],
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            errors='replace'
        )
        
        print(f"AgentCore Status:")
        print(result.stdout.strip())
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to get agent status: {e}")
        if e.stderr:
            print(f"Error: {e.stderr.strip()}")
        if e.stdout:
            print(f"Output: {e.stdout.strip()}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Deploy workflow agents to AWS Bedrock AgentCore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy all workflow agents to dev
  python deploy_agentcore_agents.py --env dev
  
  # Deploy specific agent
  python deploy_agentcore_agents.py --env dev --agent orchestrator
  
  # Dry run to see what would be deployed
  python deploy_agentcore_agents.py --env dev --dry-run
  
  # List deployed agents
  python deploy_agentcore_agents.py --env dev --list

Note: This script deploys workflow agents to AgentCore. The Conversational 
Interface Agent should be deployed separately to Bedrock Agents using:
  python scripts/deploy_conversational_interface_agent.py --env dev
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
        help="Specific agent to deploy (default: all workflow agents)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making changes"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Deploy locally for development and testing (requires Docker)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List deployed agents and exit"
    )
    
    args = parser.parse_args()
    
    # Check if AgentCore CLI is available
    if not check_agentcore_cli():
        sys.exit(1)
    
    # List agents if requested
    if args.list:
        list_deployed_agents(args.env)
        sys.exit(0)
    
    # Deploy agents
    agents = [args.agent] if args.agent else None
    
    # Set environment variable for local deployment
    if args.local:
        os.environ['AGENTCORE_LOCAL_DEPLOY'] = 'true'
        print("🏠 Local deployment mode enabled")
    
    failures = deploy_all_agents(args.env, agents, args.dry_run)
    
    if failures > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()