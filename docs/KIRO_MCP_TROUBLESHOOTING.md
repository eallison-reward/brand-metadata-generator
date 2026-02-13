# Kiro IDE MCP Connection Troubleshooting

## Understanding MCP in Kiro IDE

The MCP configuration in `.kiro/settings/mcp.json` tells Kiro IDE which MCP servers to connect to, but **Kiro IDE itself needs to establish the connection**. The configuration file alone doesn't activate the servers.

## Quick Fix: Restart Kiro IDE

The most reliable way to activate MCP servers:

1. **Save all your work**
2. **Close Kiro IDE completely** (not just the window, but quit the application)
3. **Reopen Kiro IDE**
4. **Check the MCP Servers panel** in the Kiro feature sidebar

Kiro will automatically detect the configuration and connect to all enabled MCP servers.

## Checking MCP Server Status in Kiro IDE

### Method 1: MCP Servers Panel

1. Open the Kiro feature panel (sidebar)
2. Look for "MCP Servers" section
3. You should see all configured servers with their status:
   - 🟢 Connected - Server is active and ready
   - 🔴 Disconnected - Server failed to connect
   - ⚪ Disabled - Server is disabled in configuration

### Method 2: Command Palette

1. Open Command Palette (Ctrl+Shift+P or Cmd+Shift+P)
2. Type "MCP"
3. You'll see MCP-related commands:
   - "Reconnect MCP Servers" - Reconnect all servers
   - "View MCP Servers" - Open MCP servers panel
   - "Configure MCP" - Open configuration file

## Common Issues and Solutions

### Issue 1: Wikipedia MCP Shows as Disconnected

**Symptoms:**
- Wikipedia MCP appears in the list but shows as disconnected
- No error message, just not connecting

**Solutions:**

1. **Check if `uv` is installed:**
   ```bash
   uvx --version
   ```
   If not found, install it:
   ```bash
   pip install --user uv
   ```

2. **Test the Wikipedia MCP server manually:**
   ```bash
   uvx mcp-server-wikipedia --help
   ```
   This will download the server if it's not already installed.

3. **Restart Kiro IDE** after installing `uv`

4. **Check Kiro logs** for error messages:
   - Open Output panel in Kiro
   - Select "Kiro MCP" from the dropdown
   - Look for connection errors

### Issue 2: MCP Configuration Not Recognized

**Symptoms:**
- No MCP servers appear in the panel
- Configuration file exists but Kiro doesn't see it

**Solutions:**

1. **Verify file location:**
   - File should be at: `.kiro/settings/mcp.json`
   - Check you're in the correct workspace folder

2. **Validate JSON syntax:**
   - Open `.kiro/settings/mcp.json` in Kiro
   - Look for syntax errors (red squiggles)
   - Ensure all brackets and quotes are balanced

3. **Check workspace configuration:**
   - If using multi-root workspace, each folder can have its own config
   - User-level config is at: `~/.kiro/settings/mcp.json`
   - Workspace config overrides user config

4. **Restart Kiro IDE completely**

### Issue 3: MCP Server Fails to Start

**Symptoms:**
- Server shows as disconnected with error message
- Kiro logs show connection failures

**Solutions:**

1. **Check the command is correct:**
   ```json
   "wikipedia": {
     "command": "uvx",  // Must be "uvx" not "uv"
     "args": ["mcp-server-wikipedia"]  // Correct package name
   }
   ```

2. **Verify the MCP server package exists:**
   ```bash
   uvx mcp-server-wikipedia --help
   ```

3. **Check for port conflicts:**
   - MCP servers use local ports
   - Close other applications that might conflict
   - Restart Kiro IDE

4. **Check firewall/antivirus:**
   - Some security software blocks local server connections
   - Add Kiro IDE to allowed applications

### Issue 4: Brand Registry MCP Not Connecting

**Symptoms:**
- Brand Registry MCP shows as disconnected
- Error about Python module not found

**Solutions:**

1. **Verify Python environment:**
   ```bash
   python -m mcp_servers.brand_registry.server --help
   ```

2. **Check Python path:**
   - Kiro needs to find your Python installation
   - Ensure Python is in your PATH

3. **Install dependencies:**
   ```bash
   pip install boto3 pyathena
   ```

4. **Set AWS credentials:**
   ```powershell
   $env:AWS_ACCESS_KEY_ID = "your-key"
   $env:AWS_SECRET_ACCESS_KEY = "your-secret"
   $env:AWS_REGION = "eu-west-1"
   ```

5. **Restart Kiro IDE** after setting environment variables

## Manual Reconnection

If restarting doesn't work, try manual reconnection:

1. **Open Command Palette** (Ctrl+Shift+P)
2. **Type:** "Reconnect MCP Servers"
3. **Select the command**
4. **Wait for connection** (check MCP Servers panel)

## Verifying MCP Tools Are Available

Once connected, you can verify MCP tools are available:

1. **Open a chat with Kiro**
2. **Type:** "What MCP tools do you have access to?"
3. **Kiro should list:**
   - Brand Registry tools (search_brands, get_brand_info, validate_sector)
   - Wikipedia tools (search, get_page, get_summary)

## Configuration File Reference

Your `.kiro/settings/mcp.json` should look like this:

```json
{
  "mcpServers": {
    "brand-registry": {
      "command": "python",
      "args": ["-m", "mcp_servers.brand_registry.server"],
      "env": {
        "AWS_REGION": "eu-west-1",
        "AWS_ACCESS_KEY_ID": "${AWS_ACCESS_KEY_ID}",
        "AWS_SECRET_ACCESS_KEY": "${AWS_SECRET_ACCESS_KEY}"
      },
      "disabled": false
    },
    "wikipedia": {
      "command": "uvx",
      "args": ["mcp-server-wikipedia"],
      "env": {},
      "disabled": false
    },
    "brave-search": {
      "command": "uvx",
      "args": ["mcp-server-brave-search"],
      "disabled": true
    },
    "crunchbase": {
      "command": "uvx",
      "args": ["mcp-server-crunchbase"],
      "disabled": true
    }
  }
}
```

## Still Having Issues?

1. **Check Kiro version** - Ensure you're running the latest version
2. **Check Kiro logs** - Output panel > "Kiro MCP" for detailed errors
3. **Try user-level config** - Move config to `~/.kiro/settings/mcp.json` to test
4. **Disable other MCP servers** - Test with just Wikipedia to isolate issues
5. **Check system resources** - Ensure enough memory/CPU for MCP servers

## Expected Behavior

When everything is working correctly:

- ✅ MCP Servers panel shows "wikipedia" as connected
- ✅ MCP Servers panel shows "brand-registry" as connected
- ✅ Kiro can access Wikipedia and Brand Registry tools
- ✅ Commercial Assessment Agent can validate brands using both sources

## Testing Without Kiro IDE

The Python test script (`scripts/test_mcp_connection.py`) only checks if the configuration file is valid, not if Kiro IDE is connected. To test actual MCP functionality, you need to use Kiro IDE's MCP features.
