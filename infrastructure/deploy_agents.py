#!/usr/bin/env python3
"""Deploy all agents to AWS Bedrock AgentCore.

Usage:
    python deploy_agents.py --env dev
    python deploy_agents.py --env prod --agent orchestrator
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


AGENTS = [
    "orchestrator",
    "data_transformation",
    "evaluator",
    "metadata_production",
    "commercial_assessment",
    "confirmation",
    "tiebreaker",
]

AGENT_CONFIG = {
    "orchestrator": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 600,
        "memory_size": 2048,
    },
    "data_transformation": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 900,
        "memory_size": 3072,
    },
    "evaluator": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 300,
        "memory_size": 2048,
    },
    "metadata_production": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 300,
        "memory_size": 2048,
    },
    "commercial_assessment": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 180,
        "memory_size": 1024,
    },
    "confirmation": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 300,
        "memory_size": 2048,
    },
    "tiebreaker": {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "timeout": 180,
        "memory_size": 1024,
    },
}


def deploy_agent(agent_name: str, env: str) -> bool:
    """Deploy a single agent to AgentCore.
    
    Args:
        agent_name: Name of the agent to deploy
        env: Environment (dev, staging, prod)
        
    Returns:
        True if deployment successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Deploying {agent_name} agent to {env} environment...")
    print(f"{'='*60}")
    
    agent_path = Path(f"../agents/{agent_name}")
    if not agent_path.exists():
        print(f"❌ Error: Agent directory not found: {agent_path}")
        return False
    
    handler_path = agent_path / "agentcore_handler.py"
    if not handler_path.exists():
        print(f"❌ Error: Handler not found: {handler_path}")
        return False
    
    config = AGENT_CONFIG.get(agent_name, {})
    agent_full_name = f"{agent_name}-agent-{env}"
    
    # Configure agent
    print(f"\n📝 Configuring {agent_full_name}...")
    config_cmd = [
        "agentcore", "configure",
        "--entrypoint", str(handler_path),
        "--agent-name", agent_full_name,
        "--model", config.get("model", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
        "--timeout", str(config.get("timeout", 300)),
        "--memory-size", str(config.get("memory_size", 1024)),
        "--non-interactive"
    ]
    
    try:
        result = subprocess.run(config_cmd, check=True, capture_output=True, text=True)
        print(f"✅ Configuration successful")
    except subprocess.CalledProcessError as e:
        print(f"❌ Configuration failed: {e.stderr}")
        return False
    
    # Launch agent
    print(f"\n🚀 Launching {agent_full_name}...")
    launch_cmd = ["agentcore", "launch", "--alias", env]
    
    try:
        result = subprocess.run(launch_cmd, check=True, capture_output=True, text=True)
        print(f"✅ Launch successful")
        print(f"\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Launch failed: {e.stderr}")
        return False
    
    # Set up memory
    print(f"\n💾 Setting up memory for {agent_full_name}...")
    memory_cmd = [
        "agentcore", "memory", "create",
        "--agent-name", agent_full_name,
        "--memory-type", "dynamodb",
        "--ttl-days", "30"
    ]
    
    try:
        result = subprocess.run(memory_cmd, check=True, capture_output=True, text=True)
        print(f"✅ Memory setup successful")
    except subprocess.CalledProcessError as e:
        # Memory might already exist, which is okay
        if "already exists" in e.stderr.lower():
            print(f"ℹ️  Memory already configured")
        else:
            print(f"⚠️  Memory setup warning: {e.stderr}")
    
    print(f"\n✅ Successfully deployed {agent_full_name}")
    return True


def deploy_all_agents(env: str, agents: Optional[List[str]] = None) -> int:
    """Deploy all or specified agents.
    
    Args:
        env: Environment to deploy to
        agents: Optional list of specific agents to deploy
        
    Returns:
        Number of failed deployments
    """
    agents_to_deploy = agents if agents else AGENTS
    
    print(f"\n🎯 Deploying {len(agents_to_deploy)} agent(s) to {env} environment")
    print(f"Agents: {', '.join(agents_to_deploy)}\n")
    
    failures = 0
    for agent in agents_to_deploy:
        if agent not in AGENTS:
            print(f"❌ Unknown agent: {agent}")
            failures += 1
            continue
        
        if not deploy_agent(agent, env):
            failures += 1
    
    print(f"\n{'='*60}")
    print(f"Deployment Summary")
    print(f"{'='*60}")
    print(f"Total agents: {len(agents_to_deploy)}")
    print(f"Successful: {len(agents_to_deploy) - failures}")
    print(f"Failed: {failures}")
    
    return failures


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Deploy agents to AWS Bedrock AgentCore"
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
    
    args = parser.parse_args()
    
    agents = [args.agent] if args.agent else None
    failures = deploy_all_agents(args.env, agents)
    
    sys.exit(failures)


if __name__ == "__main__":
    main()
