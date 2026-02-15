#!/usr/bin/env python3
"""Test the deployed Conversational Interface Agent.

This script tests the agent by invoking it with sample queries.
"""

import argparse
import json
import boto3
import uuid
from typing import Dict, Any

AWS_REGION = "eu-west-1"


def invoke_agent(
    agent_id: str,
    agent_alias_id: str,
    session_id: str,
    prompt: str
) -> Dict[str, Any]:
    """Invoke the Bedrock agent with a prompt.
    
    Args:
        agent_id: Agent ID
        agent_alias_id: Agent alias ID
        session_id: Session ID for conversation continuity
        prompt: User prompt
        
    Returns:
        Agent response
    """
    client = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)
    
    print(f"\n{'='*70}")
    print(f"Invoking agent with prompt: {prompt}")
    print(f"{'='*70}\n")
    
    try:
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=prompt
        )
        
        # Process event stream
        event_stream = response['completion']
        full_response = ""
        
        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    text = chunk['bytes'].decode('utf-8')
                    full_response += text
                    print(text, end='', flush=True)
        
        print("\n")
        
        return {
            'success': True,
            'response': full_response
        }
        
    except Exception as e:
        print(f"❌ Error invoking agent: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Conversational Interface Agent"
    )
    parser.add_argument(
        "--agent-id",
        default="GZF9REHEAO",
        help="Agent ID (default: GZF9REHEAO)"
    )
    parser.add_argument(
        "--alias-id",
        default="XWTFA4KL42",
        help="Agent alias ID (default: XWTFA4KL42)"
    )
    parser.add_argument(
        "--prompt",
        help="Custom prompt to test (if not provided, runs predefined tests)"
    )
    
    args = parser.parse_args()
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    if args.prompt:
        # Test custom prompt
        result = invoke_agent(
            args.agent_id,
            args.alias_id,
            session_id,
            args.prompt
        )
        
        if result['success']:
            print("✅ Test completed successfully")
        else:
            print("❌ Test failed")
    else:
        # Run predefined test suite
        test_prompts = [
            "What brands are available to process?",
            "Show me the first 5 unprocessed brands",
            "What are the workflow statistics for the last day?",
        ]
        
        print(f"\n{'='*70}")
        print(f"Running Test Suite")
        print(f"{'='*70}")
        print(f"Agent ID: {args.agent_id}")
        print(f"Alias ID: {args.alias_id}")
        print(f"Session ID: {session_id}")
        print(f"Number of tests: {len(test_prompts)}")
        
        results = []
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n\nTest {i}/{len(test_prompts)}")
            result = invoke_agent(
                args.agent_id,
                args.alias_id,
                session_id,
                prompt
            )
            results.append({
                'prompt': prompt,
                'success': result['success']
            })
        
        # Summary
        print(f"\n{'='*70}")
        print(f"Test Summary")
        print(f"{'='*70}")
        
        successful = sum(1 for r in results if r['success'])
        print(f"Total tests: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {len(results) - successful}")
        
        if successful == len(results):
            print("\n✅ All tests passed!")
        else:
            print("\n⚠️  Some tests failed")
            for i, result in enumerate(results, 1):
                if not result['success']:
                    print(f"   Test {i}: {result['prompt']}")


if __name__ == "__main__":
    main()
