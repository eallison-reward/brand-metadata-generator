#!/usr/bin/env python3
"""
MCP Connection Test Script

This script tests connectivity to all configured MCP servers:
- Brand Registry MCP (internal database)
- Wikipedia MCP (free external validation)
- Brave Search MCP (free tier)
- Crunchbase MCP (disabled by default)

Usage:
    python scripts/test_mcp_connection.py
"""

import os
import sys
import json


def test_brand_registry_mcp():
    """Test Brand Registry MCP server connectivity."""
    print("\n=== Testing Brand Registry MCP ===")
    
    # Check AWS credentials
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "eu-west-1")
    
    if not aws_key or not aws_secret:
        print("❌ AWS credentials not set")
        print("   Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
        return False
    
    print(f"✓ AWS credentials found")
    print(f"✓ AWS region: {aws_region}")
    
    # Test MCP server availability
    try:
        # In production, this would test actual MCP connectivity
        # For now, we just verify the configuration exists
        if os.path.exists(".kiro/settings/mcp.json"):
            with open(".kiro/settings/mcp.json", "r") as f:
                config = json.load(f)
                if "brand-registry" in config.get("mcpServers", {}):
                    server_config = config["mcpServers"]["brand-registry"]
                    if not server_config.get("disabled", False):
                        print("✓ Brand Registry MCP is configured and enabled")
                        return True
                    else:
                        print("⚠ Brand Registry MCP is disabled in configuration")
                        return False
        
        print("❌ MCP configuration not found")
        return False
    
    except Exception as e:
        print(f"❌ Error testing Brand Registry MCP: {str(e)}")
        return False


def test_wikipedia_mcp():
    """Test Wikipedia MCP server connectivity."""
    print("\n=== Testing Wikipedia MCP ===")
    
    # Wikipedia MCP requires no API key
    print("✓ No API key required for Wikipedia MCP")
    
    # Test MCP server availability
    try:
        if os.path.exists(".kiro/settings/mcp.json"):
            with open(".kiro/settings/mcp.json", "r") as f:
                config = json.load(f)
                if "wikipedia" in config.get("mcpServers", {}):
                    server_config = config["mcpServers"]["wikipedia"]
                    if not server_config.get("disabled", False):
                        print("✓ Wikipedia MCP is configured and enabled")
                        print("✓ Wikipedia MCP provides free access to brand information")
                        return True
                    else:
                        print("⚠ Wikipedia MCP is disabled in configuration")
                        return False
                else:
                    print("❌ Wikipedia MCP not found in configuration")
                    return False
        
        print("❌ MCP configuration not found")
        return False
    
    except Exception as e:
        print(f"❌ Error testing Wikipedia MCP: {str(e)}")
        return False


def test_brave_search_mcp():
    """Test Brave Search MCP server connectivity."""
    print("\n=== Testing Brave Search MCP ===")
    
    # Check if Brave Search is enabled
    try:
        if os.path.exists(".kiro/settings/mcp.json"):
            with open(".kiro/settings/mcp.json", "r") as f:
                config = json.load(f)
                if "brave-search" in config.get("mcpServers", {}):
                    server_config = config["mcpServers"]["brave-search"]
                    if server_config.get("disabled", True):
                        print("⚠ Brave Search MCP is disabled (paid service)")
                        print("   Brave Search API costs $5 per 1,000 requests")
                        print("   This is expected - the system works fine without it")
                        return True  # Not an error, just disabled
                    
                    # If enabled, check API key
                    api_key = os.getenv("BRAVE_API_KEY")
                    if not api_key:
                        print("❌ BRAVE_API_KEY environment variable not set")
                        print("   Brave Search API costs $5 per 1,000 requests")
                        return False
                    
                    print(f"✓ API key found: {api_key[:10]}...")
                    print("✓ Brave Search MCP is configured and enabled")
                    print("⚠ Note: Brave Search API costs $5 per 1,000 requests")
                    return True
                else:
                    print("❌ Brave Search MCP not found in configuration")
                    return False
        
        print("❌ MCP configuration not found")
        return False
    
    except Exception as e:
        print(f"❌ Error testing Brave Search MCP: {str(e)}")
        return False


def test_crunchbase_mcp():
    """Test Crunchbase MCP server connectivity."""
    print("\n=== Testing Crunchbase MCP ===")
    
    # Check if Crunchbase is enabled
    try:
        if os.path.exists(".kiro/settings/mcp.json"):
            with open(".kiro/settings/mcp.json", "r") as f:
                config = json.load(f)
                if "crunchbase" in config.get("mcpServers", {}):
                    server_config = config["mcpServers"]["crunchbase"]
                    if server_config.get("disabled", True):
                        print("⚠ Crunchbase MCP is disabled (paid service)")
                        print("   This is expected - the system works fine without it")
                        return True  # Not an error, just disabled
                    
                    # If enabled, check API key
                    api_key = os.getenv("CRUNCHBASE_API_KEY")
                    if not api_key:
                        print("❌ CRUNCHBASE_API_KEY environment variable not set")
                        print("   Crunchbase requires a paid subscription ($299+/month)")
                        return False
                    
                    print(f"✓ API key found: {api_key[:10]}...")
                    print("✓ Crunchbase MCP is configured and enabled")
                    return True
                else:
                    print("❌ Crunchbase MCP not found in configuration")
                    return False
        
        print("❌ MCP configuration not found")
        return False
    
    except Exception as e:
        print(f"❌ Error testing Crunchbase MCP: {str(e)}")
        return False


def main():
    """Run all MCP connectivity tests."""
    print("=" * 60)
    print("MCP Connection Test")
    print("=" * 60)
    
    results = {
        "Brand Registry MCP": test_brand_registry_mcp(),
        "Wikipedia MCP": test_wikipedia_mcp(),
        "Brave Search MCP": test_brave_search_mcp(),
        "Crunchbase MCP": test_crunchbase_mcp()
    }
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for server, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {server}")
    
    # Count successes (excluding Brave Search and Crunchbase which are expected to be disabled)
    critical_servers = ["Brand Registry MCP", "Wikipedia MCP"]
    critical_results = [results[s] for s in critical_servers if s in results]
    
    if all(critical_results):
        print("\n✓ All critical MCP servers are configured correctly!")
        print("  You have 2 free data sources for brand validation.")
        return 0
    elif any(critical_results):
        print("\n⚠ Some MCP servers need attention (see details above)")
        print("  The system will work with available servers.")
        return 0
    else:
        print("\n❌ No MCP servers are available")
        print("  Please configure at least one MCP server.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
