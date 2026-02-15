#!/usr/bin/env python3
"""Direct test of conversational interface agent with DynamoDB backend."""

import boto3
import json
import sys
import argparse
from typing import Dict, Any


def test_agent_conversation(
    agent_id: str,
    alias_id: str,
    region: str = "eu-west-1"
) -> bool:
    """Test agent conversation functionality.
    
    Args:
        agent_id: Bedrock agent ID
        alias_id: Agent alias ID
        region: AWS region
        
    Returns:
        True if test passes, False otherwise
    """
    print(f"🤖 Testing agent conversation...")
    print(f"   Agent ID: {agent_id}")
    print(f"   Alias ID: {alias_id}")
    print(f"   Region: {region}")
    print()
    
    # Initialize Bedrock Agent Runtime client
    bedrock_runtime = boto3.client('bedrock-agent-runtime', region_name=region)
    
    # Test query: Ask for brands to check
    test_query = "please show me the brands in the check table that need processing"
    
    try:
        print(f"📝 Sending query: '{test_query}'")
        
        response = bedrock_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId="test-session-001",
            inputText=test_query
        )
        
        # Process response stream
        response_text = ""
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    response_text += chunk['bytes'].decode('utf-8')
        
        print(f"🤖 Agent response:")
        print(response_text)
        print()
        
        # Check if response contains expected elements
        success_indicators = [
            "brand",  # Should mention brands
            "processing" or "unprocessed",  # Should mention status
            "table" or "database",  # Should reference data source
        ]
        
        response_lower = response_text.lower()
        found_indicators = [indicator for indicator in success_indicators 
                          if any(word in response_lower for word in indicator.split(" or "))]
        
        if len(found_indicators) >= 2:
            print("✅ Agent response looks good!")
            return True
        else:
            print("⚠️  Agent response may not be working correctly")
            print(f"   Found indicators: {found_indicators}")
            return False
            
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        return False


def test_dynamodb_direct(table_name: str, region: str = "eu-west-1") -> bool:
    """Test DynamoDB table directly.
    
    Args:
        table_name: DynamoDB table name
        region: AWS region
        
    Returns:
        True if test passes, False otherwise
    """
    print(f"🗄️  Testing DynamoDB table directly...")
    print(f"   Table: {table_name}")
    print(f"   Region: {region}")
    print()
    
    try:
        dynamodb = boto3.resource('dynamodb', region_name=region)
        table = dynamodb.Table(table_name)
        
        # Scan table for a few records
        response = table.scan(Limit=5)
        items = response.get('Items', [])
        
        print(f"📊 Found {len(items)} sample records:")
        for i, item in enumerate(items, 1):
            brandid = item.get('brandid', 'N/A')
            brandname = item.get('brandname', 'N/A')
            status = item.get('status', 'N/A')
            sector = item.get('sector', 'N/A')
            print(f"   {i}. Brand {brandid}: {brandname} ({sector}) - {status}")
        
        if items:
            print("✅ DynamoDB table is accessible and contains data!")
            return True
        else:
            print("⚠️  DynamoDB table is empty or inaccessible")
            return False
            
    except Exception as e:
        print(f"❌ DynamoDB test failed: {e}")
        return False


def get_agent_info(env: str, region: str = "eu-west-1") -> tuple:
    """Get agent ID and alias ID for environment.
    
    Args:
        env: Environment name
        region: AWS region
        
    Returns:
        Tuple of (agent_id, alias_id) or (None, None) if not found
    """
    try:
        bedrock_agent = boto3.client('bedrock-agent', region_name=region)
        
        # List agents to find our agent
        agent_name = f"brand_metagen_conversational_interface_{env}"
        
        response = bedrock_agent.list_agents()
        agent = next(
            (a for a in response.get('agentSummaries', []) 
             if a['agentName'] == agent_name),
            None
        )
        
        if not agent:
            print(f"❌ Agent not found: {agent_name}")
            return None, None
        
        agent_id = agent['agentId']
        
        # Get alias ID
        aliases_response = bedrock_agent.list_agent_aliases(agentId=agent_id)
        alias = next(
            (a for a in aliases_response.get('agentAliasSummaries', []) 
             if a['agentAliasName'] == env),
            None
        )
        
        if not alias:
            print(f"❌ Agent alias not found: {env}")
            return agent_id, None
        
        alias_id = alias['agentAliasId']
        return agent_id, alias_id
        
    except Exception as e:
        print(f"❌ Failed to get agent info: {e}")
        return None, None


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test conversational interface agent")
    parser.add_argument(
        "--env",
        default="dev",
        help="Environment to test"
    )
    parser.add_argument(
        "--region",
        default="eu-west-1",
        help="AWS region"
    )
    parser.add_argument(
        "--agent-id",
        help="Specific agent ID to test (will auto-discover if not provided)"
    )
    parser.add_argument(
        "--alias-id",
        help="Specific alias ID to test (will auto-discover if not provided)"
    )
    parser.add_argument(
        "--skip-agent-test",
        action="store_true",
        help="Skip agent conversation test"
    )
    parser.add_argument(
        "--skip-dynamodb-test",
        action="store_true",
        help="Skip DynamoDB direct test"
    )
    
    args = parser.parse_args()
    
    print("🧪 Testing conversational interface agent with DynamoDB...")
    print(f"   Environment: {args.env}")
    print(f"   Region: {args.region}")
    print()
    
    success = True
    
    # Test DynamoDB directly
    if not args.skip_dynamodb_test:
        table_name = f"brand_processing_status_{args.env}"
        if not test_dynamodb_direct(table_name, args.region):
            success = False
        print()
    
    # Test agent conversation
    if not args.skip_agent_test:
        # Get agent info
        if args.agent_id and args.alias_id:
            agent_id, alias_id = args.agent_id, args.alias_id
        else:
            print("🔍 Discovering agent information...")
            agent_id, alias_id = get_agent_info(args.env, args.region)
        
        if agent_id and alias_id:
            if not test_agent_conversation(agent_id, alias_id, args.region):
                success = False
        else:
            print("❌ Could not find agent to test")
            success = False
    
    if success:
        print("🎉 All tests passed!")
        print("\nThe conversational interface agent is working correctly with DynamoDB!")
    else:
        print("❌ Some tests failed")
        print("\nTroubleshooting steps:")
        print("1. Verify DynamoDB table exists and is populated")
        print("2. Check Lambda function logs in CloudWatch")
        print("3. Verify agent is deployed and prepared")
        print("4. Check IAM permissions for DynamoDB access")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()