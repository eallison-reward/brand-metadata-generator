# MCP Setup Guide

This guide explains how to configure and use Model Context Protocol (MCP) servers for the Brand Metadata Generator system.

## Overview

The Brand Metadata Generator uses MCP to connect the Commercial Assessment Agent to external brand databases for accurate brand validation. This enables the system to verify brand names, sectors, and commercial information against authoritative data sources.

## Quick Start (Free Setup - No External APIs)

For most users, you only need the **Brand Registry MCP server** which is completely free and uses your existing Athena database.

### Prerequisites
- Python 3.12+
- AWS credentials configured
- Access to Athena database `brand_metadata_generator_db`

### Setup Steps

1. **Verify MCP Configuration**
   
   The Brand Registry MCP is already configured in `.kiro/settings/mcp.json` and enabled by default.

2. **Set AWS Credentials**
   
   ```powershell
   # Windows PowerShell
   $env:AWS_ACCESS_KEY_ID = "your-aws-key"
   $env:AWS_SECRET_ACCESS_KEY = "your-aws-secret"
   $env:AWS_REGION = "eu-west-1"
   ```

3. **Test the Connection**
   
   ```bash
   python scripts/test_mcp_connection.py
   ```

4. **Done!**
   
   The system will now use your internal brand database for all brand validation. No external APIs or costs required.

---

## MCP Servers

### 1. Brand Registry MCP Server (FREE - Recommended)

The **Brand Registry MCP server** provides access to your internal brand database stored in AWS Athena. This is the **primary and recommended** MCP server for the system.

**Cost:** FREE (uses your existing AWS Athena database)

**Features:**
- Access to all 3,000+ brands in your database
- Real-time data from your combo and MCC tables
- No external API dependencies
- No additional costs

**Status:** ✓ Enabled by default

### 2. Wikipedia MCP Server (FREE - Recommended)

The **Wikipedia MCP server** provides free access to Wikipedia data for brand validation.

**Cost:** FREE (no API key required)

**Features:**
- Access to millions of company and brand articles
- Good coverage of major international brands
- No rate limits
- No API key required
- Completely free

**Status:** ✓ Enabled by default

**Installation:**
The Wikipedia MCP server is automatically installed when you use the `uvx` command. No manual installation or API key required.

### 3. Brave Search MCP Server (FREE Tier - Recommended)

The **Brave Search MCP server** provides web search capabilities for brand validation.

**Cost:** FREE tier with 2,000 queries/month

**Features:**
- Web search for brand information
- Good for finding recent company information
- Free tier: 2,000 queries/month
- Easy API key setup (free)

**Status:** ✓ Enabled by default

**API Key Setup:**

1. **Get a Free Brave Search API Key:**
   - Visit [Brave Search API](https://brave.com/search/api/)
   - Click "Get Started" or "Sign Up"
   - Create a free account
   - Navigate to your dashboard and copy your API key

2. **Set Environment Variable:**

   **Windows (PowerShell):**
   ```powershell
   $env:BRAVE_API_KEY = "your-api-key-here"
   ```

   **Windows (Command Prompt):**
   ```cmd
   set BRAVE_API_KEY=your-api-key-here
   ```

   **Linux/macOS:**
   ```bash
   export BRAVE_API_KEY="your-api-key-here"
   ```

3. **Persistent Environment Variable (Recommended):**

   **Windows:**
   - Open System Properties > Environment Variables
   - Add a new User or System variable:
     - Name: `BRAVE_API_KEY`
     - Value: `your-api-key-here`

   **Linux/macOS:**
   - Add to `~/.bashrc` or `~/.zshrc`:
     ```bash
     export BRAVE_API_KEY="your-api-key-here"
     ```
   - Reload: `source ~/.bashrc`

### 4. Crunchbase MCP Server (PAID - Optional)

The Crunchbase MCP server provides access to external company data from Crunchbase.

**Cost:** PAID - Crunchbase API requires a paid subscription (starting at $299+/month)

**Status:** ✗ Disabled by default (to avoid costs)

**Note:** This is an **optional enhancement** only. The system works perfectly without it using the Brand Registry MCP and internal database fallback.

#### Should You Enable Crunchbase?

**You DON'T need Crunchbase if:**
- ✓ Your brands are already in the Athena database (which they are - 3,000+ brands)
- ✓ You're working with known retail brands
- ✓ You don't have budget for external APIs
- ✓ You're in development/testing phase

**You MIGHT want Crunchbase if:**
- You need to validate completely new brands not in your database
- You need external validation for compliance/audit purposes
- You have budget for API subscriptions ($299+/month)
- You're in production and need maximum validation coverage

#### Crunchbase Installation (Only if you have a paid account)

The Crunchbase MCP server is automatically installed when you use the `uvx` command. No manual installation is required.

#### Configuration

The MCP configuration is stored in `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "crunchbase": {
      "command": "uvx",
      "args": ["mcp-server-crunchbase"],
      "env": {
        "CRUNCHBASE_API_KEY": "${CRUNCHBASE_API_KEY}"
      },
      "disabled": false,
      "autoApprove": [
        "search_organizations",
        "get_organization",
        "search_people"
      ]
    }
  }
}
```

#### API Key Setup

1. **Obtain a Crunchbase API Key:**
   - Visit [Crunchbase API](https://data.crunchbase.com/docs/using-the-api)
   - Sign up for an account or log in
   - Navigate to API settings and generate an API key
   - Copy the API key

2. **Set Environment Variable:**

   **Windows (PowerShell):**
   ```powershell
   $env:CRUNCHBASE_API_KEY = "your-api-key-here"
   ```

   **Windows (Command Prompt):**
   ```cmd
   set CRUNCHBASE_API_KEY=your-api-key-here
   ```

   **Linux/macOS:**
   ```bash
   export CRUNCHBASE_API_KEY="your-api-key-here"
   ```

3. **Persistent Environment Variable (Recommended):**

   **Windows:**
   - Open System Properties > Environment Variables
   - Add a new User or System variable:
     - Name: `CRUNCHBASE_API_KEY`
     - Value: `your-api-key-here`

   **Linux/macOS:**
   - Add to `~/.bashrc` or `~/.zshrc`:
     ```bash
     export CRUNCHBASE_API_KEY="your-api-key-here"
     ```
   - Reload: `source ~/.bashrc`

#### Testing the Connection

To test the Crunchbase MCP server connection:

```python
# Test script: test_crunchbase_mcp.py
import os
import subprocess
import json

def test_crunchbase_connection():
    """Test Crunchbase MCP server connectivity."""
    api_key = os.getenv("CRUNCHBASE_API_KEY")
    
    if not api_key:
        print("❌ CRUNCHBASE_API_KEY environment variable not set")
        return False
    
    print(f"✓ API key found: {api_key[:10]}...")
    
    # Test MCP server
    try:
        result = subprocess.run(
            ["uvx", "mcp-server-crunchbase", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✓ Crunchbase MCP server is accessible")
            return True
        else:
            print(f"❌ MCP server error: {result.stderr}")
            return False
    
    except Exception as e:
        print(f"❌ Connection test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_crunchbase_connection()
    exit(0 if success else 1)
```

Run the test:
```bash
python test_crunchbase_mcp.py
```

## Available MCP Tools

### Brand Registry Tools (Custom - Internal Database)

1. **search_brands**
   - Search for brands in the internal database
   - Parameters: `query` (string), `sector` (optional)
   - Returns: List of matching brands with brandid, brandname, sector

2. **get_brand_info**
   - Get detailed information about a specific brand
   - Parameters: `brandid` (integer)
   - Returns: Complete brand profile including combo count, MCCID distribution

3. **validate_sector**
   - Validate if a sector classification is appropriate for a brand
   - Parameters: `brandid` (integer), `sector` (string)
   - Returns: Validation result with confidence score

### Wikipedia Tools

1. **search**
   - Search Wikipedia for articles
   - Parameters: `query` (string)
   - Returns: List of matching articles with titles and snippets

2. **get_page**
   - Get full content of a Wikipedia page
   - Parameters: `title` (string)
   - Returns: Complete page content including text, categories, links

3. **get_summary**
   - Get summary of a Wikipedia page
   - Parameters: `title` (string)
   - Returns: Brief summary of the page

### Brave Search Tools

1. **brave_web_search**
   - Search the web for information
   - Parameters: `query` (string), `count` (optional, default 10)
   - Returns: Web search results with titles, URLs, descriptions

2. **brave_local_search**
   - Search for local businesses
   - Parameters: `query` (string), `count` (optional)
   - Returns: Local business results

### Crunchbase Tools (Disabled by Default)

1. **search_organizations**
   - Search for organizations by name
   - Parameters: `query` (string)
   - Returns: List of matching organizations with basic info

2. **get_organization**
   - Get detailed information about a specific organization
   - Parameters: `organization_id` (string)
   - Returns: Complete organization profile including sector, industry, description

3. **search_people**
   - Search for people by name
   - Parameters: `query` (string)
   - Returns: List of matching people with affiliations



## Usage in Commercial Assessment Agent

The Commercial Assessment Agent uses MCP tools to validate brands with a multi-tier approach:

```python
# Example usage in agent code
from agents.commercial_assessment.tools import verify_brand_exists

# The agent will automatically use MCP if configured
result = verify_brand_exists("Starbucks")

# Result includes MCP data with source priority:
# Tier 1: Brand Registry MCP (internal database) - confidence 0.95
# Tier 2: Wikipedia MCP (free external) - confidence 0.88
# Tier 3: Brave Search MCP (free tier) - confidence 0.82
# Tier 4: Crunchbase MCP (paid, disabled) - confidence 0.90
# Tier 5: Web search fallback - confidence 0.70
# Tier 6: Internal known brands - confidence varies

# Example result:
# {
#     "exists": True,
#     "confidence": 0.88,
#     "source": "wikipedia_mcp",
#     "official_name": "Starbucks Corporation",
#     "primary_sector": "Food & Beverage"
# }
```

## Testing MCP Servers

You can test all MCP servers using the test script:

```bash
python scripts/test_mcp_connection.py
```

This will test:
- Brand Registry MCP (requires AWS credentials)
- Wikipedia MCP (no credentials needed)
- Brave Search MCP (requires BRAVE_API_KEY)
- Crunchbase MCP (disabled by default)

## Troubleshooting

### MCP Server Not Found

**Error:** `uvx: command not found` or `mcp-server-wikipedia not found`

**Solution:**
1. Install `uv` package manager (no admin permissions required):
   ```bash
   # Option 1: Using pip (easiest)
   pip install --user uv
   
   # Option 2: Windows (PowerShell)
   irm https://astral.sh/uv/install.ps1 | iex
   
   # Option 3: Linux/macOS
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Verify installation:
   ```bash
   uvx --version
   ```

3. Restart your terminal after installation

### API Key Not Working

**Error:** `Authentication failed` or `Invalid API key`

**Solution for Brave Search:**
1. Verify the API key is correct
2. Check that the environment variable is set:
   ```bash
   # Windows PowerShell
   echo $env:BRAVE_API_KEY
   
   # Linux/macOS
   echo $BRAVE_API_KEY
   ```
3. Restart your terminal/IDE after setting the environment variable
4. Verify you haven't exceeded the free tier limit (2,000 queries/month)
5. Check your Brave Search API dashboard for usage statistics

**Solution for Crunchbase (if enabled):**
1. Verify the API key is correct
2. Check that the environment variable is set:
   ```bash
   # Windows PowerShell
   echo $env:CRUNCHBASE_API_KEY
   
   # Linux/macOS
   echo $CRUNCHBASE_API_KEY
   ```
3. Restart your terminal/IDE after setting the environment variable
4. Verify API key has not expired in Crunchbase dashboard

### Connection Timeout

**Error:** `Connection timeout` or `MCP server not responding`

**Solution:**
1. Check internet connectivity
2. Verify firewall is not blocking the connection
3. Try increasing timeout in agent configuration
4. Check Crunchbase API status page

### Rate Limiting

**Error:** `Rate limit exceeded` or `Too many requests`

**Solution:**
1. Implement caching in the Commercial Assessment Agent (see Requirement 15.10)
2. Reduce query frequency
3. Upgrade Crunchbase API plan if needed
4. Use fallback to web search when rate limited

## Monitoring MCP Usage

The system logs all MCP interactions for monitoring and debugging:

```python
# MCP logs are stored in CloudWatch
# Log group: /aws/lambda/brand_metagen_commercial_assessment

# Example log entry:
{
    "timestamp": "2024-02-13T10:30:00Z",
    "agent": "commercial_assessment",
    "mcp_server": "crunchbase",
    "tool": "search_organizations",
    "query": "Starbucks",
    "response_time_ms": 245,
    "success": true,
    "cached": false
}
```

## Best Practices

1. **Always set environment variables persistently** to avoid connection issues
2. **Implement caching** to reduce API calls and improve performance
3. **Use fallback mechanisms** when MCP is unavailable
4. **Monitor API usage** to stay within rate limits
5. **Log all MCP interactions** for audit and debugging
6. **Test MCP connectivity** before deploying to production
7. **Keep API keys secure** - never commit them to version control

## Security Considerations

1. **Never commit API keys** to Git repositories
2. **Use environment variables** for all sensitive credentials
3. **Rotate API keys** regularly
4. **Limit API key permissions** to only required scopes
5. **Monitor API key usage** for suspicious activity
6. **Use AWS Secrets Manager** for production deployments

## Summary of MCP Servers

| MCP Server | Cost | API Key Required | Status | Confidence | Use Case |
|------------|------|------------------|--------|------------|----------|
| Brand Registry | FREE | AWS credentials | ✓ Enabled | 0.95 | Internal database (3,000+ brands) |
| Wikipedia | FREE | No | ✓ Enabled | 0.88 | Major brands, international coverage |
| Brave Search | FREE (2k/mo) | Yes (free) | ✓ Enabled | 0.82 | Recent info, broad coverage |
| Crunchbase | PAID ($299+/mo) | Yes (paid) | ✗ Disabled | 0.90 | Optional external validation |

## Recommended Setup

For most users, the following setup provides excellent brand validation at zero cost:

1. **Brand Registry MCP** (already configured) - Your primary source
2. **Wikipedia MCP** (just added) - Free external validation
3. **Brave Search MCP** (just added) - Free tier for additional coverage

This gives you 3 free data sources with good coverage of retail brands.

## Next Steps

1. Set up Brave Search API key (free): https://brave.com/search/api/
2. Test the MCP connections: `python scripts/test_mcp_connection.py`
3. The system will automatically use all enabled MCP servers in priority order
