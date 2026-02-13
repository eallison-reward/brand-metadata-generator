# MCP Connection Guide for Kiro IDE

## Understanding the Issue

You're seeing that Wikipedia MCP is **configured** but **not connected**. This is the difference:

- ✅ **Configured** = Listed in `.kiro/settings/mcp.json`
- ❌ **Connected** = Kiro IDE has established a live connection to the server

## The Solution: Restart Kiro IDE

**The configuration file alone doesn't activate MCP servers.** Kiro IDE needs to read the configuration and establish connections.

### Steps to Connect:

1. **Save all your work**
2. **Close Kiro IDE completely** (quit the application, not just close the window)
3. **Reopen Kiro IDE**
4. **Check the MCP Servers panel** in the Kiro sidebar
5. **Verify status:**
   - 🟢 `wikipedia` - Connected
   - 🟢 `brand-registry` - Connected
   - ⚪ `brave-search` - Disabled
   - ⚪ `crunchbase` - Disabled

## Alternative: Reconnect Without Restarting

If you don't want to restart:

1. Open Command Palette (Ctrl+Shift+P or Cmd+Shift+P)
2. Type: "Reconnect MCP Servers"
3. Select the command
4. Wait a few seconds
5. Check MCP Servers panel for connection status

## Verifying the Connection

### In Kiro IDE:

1. Open the Kiro feature panel (sidebar)
2. Look for "MCP Servers" section
3. Check connection status for each server

### Test with Kiro:

1. Open a chat with Kiro
2. Ask: "What MCP tools do you have access to?"
3. Kiro should list tools from connected servers

## What the Test Script Does

The Python test script (`scripts/test_mcp_connection.py`) only checks if:
- The configuration file exists
- The JSON is valid
- Servers are enabled/disabled correctly

**It does NOT test if Kiro IDE is actually connected to the servers.**

## Troubleshooting

If Wikipedia MCP still won't connect after restarting:

### 1. Check if `uv` is installed:

```bash
uvx --version
```

If not found:
```bash
pip install --user uv
```

Then restart Kiro IDE again.

### 2. Test the Wikipedia MCP server manually:

```bash
uvx mcp-server-wikipedia --help
```

This will download the server if needed.

### 3. Check Kiro logs:

1. Open Output panel in Kiro
2. Select "Kiro MCP" from the dropdown
3. Look for error messages

### 4. Verify configuration file:

Open `.kiro/settings/mcp.json` and ensure it looks like this:

```json
{
  "mcpServers": {
    "wikipedia": {
      "command": "uvx",
      "args": ["mcp-server-wikipedia"],
      "env": {},
      "disabled": false,
      "autoApprove": ["search", "get_page", "get_summary"]
    }
  }
}
```

## Common Mistakes

❌ **Thinking the configuration file alone activates servers**
✅ **Understanding that Kiro IDE needs to connect to configured servers**

❌ **Only running the Python test script**
✅ **Checking the MCP Servers panel in Kiro IDE**

❌ **Not restarting Kiro IDE after configuration changes**
✅ **Always restarting Kiro IDE after modifying mcp.json**

## Summary

1. **Configuration** (`.kiro/settings/mcp.json`) = What servers to use
2. **Connection** (Kiro IDE) = Actually connecting to those servers
3. **Restart Kiro IDE** = The most reliable way to establish connections

## Need More Help?

See the detailed troubleshooting guide:
- `docs/KIRO_MCP_TROUBLESHOOTING.md`

Or check Kiro's MCP documentation in the IDE.
