#!/usr/bin/env python3
"""Test the conversational interface agent."""

import argparse
import boto3
import sys
import time


def test_agent(agent_id: str, alias_id: str, prompt: str, region: str = "eu-west-1"):
    """Test the agent with a prompt.
    
    Args:
        agent_id: Agent ID
        alias_id: Agent alias ID
        prompt: Test prompt
        region: AWS region
    """
    bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=region)
    
    try:
        print(f"\n{'='*70}")
        print(f"Testing Conversational Agent")
        print(f"{'='*70}")
        print(f"Agent ID: {agent_id}")
        print(f"Alias ID: {alias_id}")
        print(f"Region: {region}")
        print(f"\nPrompt: {prompt}")
        print(f"\n{'='*70}")
        print(f"Response:")
        print(f"{'='*70}\n")
        
        # Invoke agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=f"test-session-{int(time.time())}",
            inputText=prompt
        )
        
        # Stream response
        event_stream = response['completion']
        full_response = ""
        
        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    text = chunk['bytes'].decode('utf-8')
                    print(text, end='', flush=True)
                    full_response += text
        
        print(f"\n\n{'='*70}")
        print(f"✅ Test completed successfully!")
        print(f"{'='*70}\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error testing agent: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test conversational interface agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with default prompt
  python test_conversational_agent.py --agent-id GZF9REHEAO --alias-id XWTFA4KL42
  
  # Test with custom prompt
  python test_conversational_agent.py --agent-id GZF9REHEAO --alias-id XWTFA4KL42 --prompt "what brands are ready to be processed?"
        """
    )
    parser.add_argument(
        "--agent-id",
        required=True,
        help="Agent ID"
    )
    parser.add_argument(
        "--alias-id",
        required=True,
        help="Agent alias ID"
    )
    parser.add_argument(
        "--prompt",
        default="what brands are ready to be processed?",
        help="Test prompt (default: 'what brands are ready to be processed?')"
    )
    parser.add_argument(
        "--region",
        default="eu-west-1",
        help="AWS region (default: eu-west-1)"
    )
    
    args = parser.parse_args()
    
    success = test_agent(args.agent_id, args.alias_id, args.prompt, args.region)
    
    if success:
        sys.exit(0)
    else:
        print("\n❌ Test failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
