# Free MCP Servers Setup Guide

This guide walks you through the free MCP servers for brand validation:
1. Brand Registry MCP (your internal database)
2. Wikipedia MCP (completely free, no API key)

## Why These MCP Servers?

Your system now has 2 completely free data sources for brand validation:
- **Brand Registry MCP** - Your internal database (3,000+ brands)
- **Wikipedia MCP** - Major brands, international coverage

Both are 100% free with no API keys or costs!

## Prerequisites

- Python 3.12+
- `uv` package manager (for running MCP servers)

## Step 1: Install uv Package Manager

The MCP servers use `uvx` to run. Install `uv` using one of these methods (no admin permissions required):

### Option 1: Using pip (Easiest)

```bash
pip install --user uv
```

### Option 2: Windows PowerShell

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

### Option 3: Linux/macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installation, restart your terminal and verify:

```bash
uvx --version
```

## Step 2: Activate Wikipedia MCP in Kiro IDE

Wikipedia MCP is configured in `.kiro/settings/mcp.json`, but you need to activate it in Kiro IDE:

### Option 1: Restart Kiro IDE (Recommended)

1. Close Kiro IDE completely
2. Reopen Kiro IDE
3. Kiro will automatically detect and connect to the Wikipedia MCP server

### Option 2: Reconnect MCP Servers

1. Open the Command Palette (Ctrl+Shift+P or Cmd+Shift+P)
2. Search for "MCP"
3. Select "Reconnect MCP Servers" or "Reload MCP Servers"
4. Kiro will reconnect to all configured MCP servers

### Option 3: Check MCP Server View

1. Open the Kiro feature panel (sidebar)
2. Look for "MCP Servers" section
3. You should see "wikipedia" listed
4. If it shows as disconnected, click to reconnect

**Note:** The Wikipedia MCP server configuration is in place, but Kiro IDE needs to establish the connection. After restarting or reconnecting, the Wikipedia MCP server will be available to the Commercial Assessment Agent.

## Step 3: Verify MCP Connection in Kiro IDE

After restarting or reconnecting, verify the Wikipedia MCP server is connected:

### Check in Kiro IDE:

1. Open the Kiro feature panel (sidebar)
2. Look for "MCP Servers" section
3. You should see:
   - `brand-registry` - Connected
   - `wikipedia` - Connected
   - `brave-search` - Disabled
   - `crunchbase` - Disabled

### Test the Configuration:

Run the test script to verify the configuration file is correct:

```bash
python scripts/test_mcp_connection.py
```

**Note:** This script only checks if the MCP servers are configured in the JSON file, not if Kiro IDE is actually connected to them. The actual connection happens within Kiro IDE.

Expected output:

```
============================================================
MCP Connection Test
============================================================

=== Testing Brand Registry MCP ===
✓ Brand Registry MCP is configured and enabled

=== Testing Wikipedia MCP ===
✓ No API key required for Wikipedia MCP
✓ Wikipedia MCP is configured and enabled
✓ Wikipedia MCP provides free access to brand information

=== Testing Brave Search MCP ===
⚠ Brave Search MCP is disabled (paid service)

=== Testing Crunchbase MCP ===
⚠ Crunchbase MCP is disabled (paid service)

✓ All critical MCP servers are configured correctly!
  You have 2 free data sources for brand validation.
```

## How It Works

When the Commercial Assessment Agent validates a brand, it queries MCP servers in this order:

1. **Brand Registry MCP** (confidence: 0.95)
   - Your internal Athena database
   - 3,000+ brands already loaded

2. **Wikipedia MCP** (confidence: 0.88)
   - Free access to Wikipedia
   - Good for major international brands
   - No rate limits

3. **Brave Search MCP** (confidence: 0.82) - DISABLED
   - Paid service ($5/1000 requests)
   - Optional external validation

4. **Crunchbase MCP** (confidence: 0.90) - DISABLED
   - Paid service ($299+/month)
   - Optional external validation

5. **Web Search Fallback** (confidence: 0.70)
   - Used if all MCP servers fail

6. **Internal Known Brands** (confidence: varies)
   - Hardcoded list of major brands
   - Last resort fallback

## Troubleshooting

### Wikipedia MCP Not Connecting in Kiro IDE

**Issue:** Wikipedia MCP shows as disconnected or not available in Kiro IDE

**Solutions:**

1. **Restart Kiro IDE** - This is the most reliable way to activate new MCP servers
2. **Check MCP Server View** - Open the Kiro feature panel and look for the MCP Servers section
3. **Reconnect MCP Servers** - Use Command Palette > "Reconnect MCP Servers"
4. **Check Kiro Logs** - Look for MCP connection errors in the Kiro output panel

### Wikipedia MCP Server Not Found

**Issue:** Kiro IDE can't find the Wikipedia MCP server

**Solution:**
```bash
# Test if uvx can access the server
uvx mcp-server-wikipedia --help

# If not found, uv will automatically download it on first use
```

### uv Not Installed

**Issue:** `uvx: command not found`

**Solution:**
```bash
# Option 1: Using pip (no admin required)
pip install --user uv

# Option 2: Windows PowerShell
irm https://astral.sh/uv/install.ps1 | iex

# Option 3: Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then restart your terminal AND restart Kiro IDE.

### MCP Configuration Not Recognized

**Issue:** Kiro IDE doesn't see the MCP configuration

**Solution:**
1. Verify the file exists: `.kiro/settings/mcp.json`
2. Check the JSON is valid (no syntax errors)
3. Restart Kiro IDE completely
4. Check if you're in a multi-root workspace (each workspace folder can have its own config)

## Cost Summary

| MCP Server | Setup Cost | Monthly Cost | Queries/Month |
|------------|------------|--------------|---------------|
| Brand Registry | FREE | FREE | Unlimited |
| Wikipedia | FREE | FREE | Unlimited |
| **Total** | **$0** | **$0** | **Unlimited** |

## Next Steps

1. Install `uv` package manager (if not already installed)
2. Run the test script to verify setup
3. Start using the Commercial Assessment Agent with 2 free data sources!

For more details, see the main [MCP Setup Guide](MCP_SETUP_GUIDE.md).
