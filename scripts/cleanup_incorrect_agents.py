#!/usr/bin/env python3
"""Remove incorrectly deployed Bedrock agents that should be on AgentCore."""

import boto3
import sys

# Agents that were incorrectly deployed to Bedrock (should be on AgentCore)
INCORRECT_AGENTS = [
    "brand_metagen_orchestrator_dev",
    "brand_metagen_data_transformation_dev", 
    "brand_metagen_evaluator_dev",
    "brand_metagen_metadata_production_dev",
    "brand_metagen_commercial_assessment_dev",
    "brand_metagen_confirmation_dev",
    "brand_metagen_tiebreaker_dev",
    "brand_metagen_feedback_processing_dev",
    "brand_metagen_learning_analytics_dev",
]

def cleanup_bedrock_agents():
    """Remove incorrectly deployed Bedrock agents."""
    bedrock_client = boto3.client('bedrock-agent', region_name='eu-west-1')
    
    print("🧹 Cleaning up incorrectly deployed Bedrock agents...")
    
    try:
        # List all agents
        response = bedrock_client.list_agents()
        agents = response.get('agentSummaries', [])
        
        deleted_count = 0
        for agent in agents:
            agent_name = agent['agentName']
            agent_id = agent['agentId']
            
            if agent_name in INCORRECT_AGENTS:
                print(f"   Deleting {agent_name} (ID: {agent_id})...")
                try:
                    bedrock_client.delete_agent(agentId=agent_id, skipResourceInUseCheck=True)
                    deleted_count += 1
                    print(f"   ✅ Deleted {agent_name}")
                except Exception as e:
                    print(f"   ❌ Failed to delete {agent_name}: {e}")
        
        print(f"\n✅ Cleanup complete. Deleted {deleted_count} incorrectly deployed agents.")
        return True
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False

if __name__ == "__main__":
    success = cleanup_bedrock_agents()
    sys.exit(0 if success else 1)