#!/usr/bin/env python3
"""Configure AgentCore agents without interactive prompts.

This script creates the .bedrock_agentcore.yaml configuration file
for all workflow agents, avoiding the need for interactive input.
"""

import yaml
from pathlib import Path
from typing import Dict, Any


# AWS Configuration
AWS_REGION = "eu-west-1"
AWS_ACCOUNT = "536824473420"

# AgentCore workflow agents
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


def create_agent_config(agent_name: str, source_path: str) -> Dict[str, Any]:
    """Create agent configuration for AgentCore.
    
    Args:
        agent_name: Name of the agent
        source_path: Path to the project root
        
    Returns:
        Agent configuration dictionary
    """
    full_agent_name = f"brand_metagen_{agent_name}"
    entrypoint_path = f"{source_path}/agents/{agent_name}/agentcore_handler.py"
    
    return {
        "name": full_agent_name,
        "language": "python",
        "node_version": "20",
        "entrypoint": entrypoint_path,
        "deployment_type": "container",  # Use container for production
        "runtime_type": None,
        "platform": "linux/arm64",
        "container_runtime": "docker",
        "source_path": source_path,
        "aws": {
            "execution_role": None,
            "execution_role_auto_create": True,
            "account": AWS_ACCOUNT,
            "region": AWS_REGION,
            "ecr_repository": None,
            "ecr_auto_create": True,
            "s3_path": None,
            "s3_auto_create": False,
            "network_configuration": {
                "network_mode": "PUBLIC",
                "network_mode_config": None
            },
            "protocol_configuration": {
                "server_protocol": "HTTP"
            },
            "observability": {
                "enabled": True
            },
            "lifecycle_configuration": {
                "idle_runtime_session_timeout": None,
                "max_lifetime": None
            }
        },
        "bedrock_agentcore": {
            "agent_id": None,
            "agent_arn": None,
            "agent_session_id": None
        },
        "codebuild": {
            "project_name": None,
            "execution_role": None,
            "source_bucket": None
        },
        "memory": {
            "mode": "STM_AND_LTM",
            "memory_id": None,  # Will be auto-created
            "memory_arn": None,
            "memory_name": f"{full_agent_name}_memory",
            "event_expiry_days": 30,
            "first_invoke_memory_check_done": False,
            "was_created_by_toolkit": True
        },
        "identity": {
            "credential_providers": [],
            "workload": None
        },
        "aws_jwt": {
            "enabled": False,
            "audiences": [],
            "signing_algorithm": "ES384",
            "issuer_url": None,
            "duration_seconds": 300
        },
        "authorizer_configuration": None,
        "request_header_configuration": {
            "requestHeaderAllowlist": [
                "Authorization",
                "X-Amzn-Bedrock-AgentCore-Runtime-Custom-+"
            ]
        },
        "oauth_configuration": None,
        "api_key_env_var_name": None,
        "api_key_credential_provider_name": None,
        "is_generated_by_agentcore_create": False
    }


def create_agentcore_config(default_agent: str = "orchestrator") -> Dict[str, Any]:
    """Create the complete AgentCore configuration.
    
    Args:
        default_agent: Name of the default agent
        
    Returns:
        Complete configuration dictionary
    """
    source_path = str(Path.cwd().resolve()).replace("\\", "/")
    
    # Create configuration for all agents
    agents_config = {}
    for agent_name in AGENTCORE_AGENTS:
        full_agent_name = f"brand_metagen_{agent_name}"
        agents_config[full_agent_name] = create_agent_config(agent_name, source_path)
    
    return {
        "default_agent": f"brand_metagen_{default_agent}",
        "agents": agents_config
    }


def write_agentcore_config(config_path: str = ".bedrock_agentcore.yaml") -> None:
    """Write the AgentCore configuration to file.
    
    Args:
        config_path: Path to write the configuration file
    """
    config = create_agentcore_config()
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"✅ Created AgentCore configuration: {config_path}")
    print(f"📝 Configured {len(AGENTCORE_AGENTS)} agents:")
    for agent in AGENTCORE_AGENTS:
        print(f"   - brand_metagen_{agent}")


def main():
    """Main entry point."""
    print("🔧 Configuring AgentCore agents...")
    
    # Check if agent handlers exist
    missing_agents = []
    for agent_name in AGENTCORE_AGENTS:
        handler_path = Path(f"agents/{agent_name}/agentcore_handler.py")
        if not handler_path.exists():
            missing_agents.append(agent_name)
    
    if missing_agents:
        print(f"❌ Missing agent handlers:")
        for agent in missing_agents:
            print(f"   - agents/{agent}/agentcore_handler.py")
        return 1
    
    # Write configuration
    write_agentcore_config()
    
    print(f"\n🎯 Next steps:")
    print(f"1. Deploy agents: python scripts/deploy_agentcore_agents.py --env dev")
    print(f"2. Check status: agentcore status")
    
    return 0


if __name__ == "__main__":
    exit(main())