# Brand Registry MCP Server

This MCP server provides access to the internal brand database stored in AWS Athena. It implements the Model Context Protocol to expose brand data to AI agents.

## Features

- **search_brands**: Search for brands by name with optional sector filtering
- **get_brand_info**: Get detailed information about a specific brand including combo count and MCCID distribution
- **validate_sector**: Validate if a sector classification is appropriate for a brand

## Installation

### Local Development

```bash
cd mcp_servers/brand_registry
pip install -e .
```

### Using uvx (Recommended)

```bash
uvx brand-registry-mcp-server
```

## Configuration

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "brand-registry": {
      "command": "python",
      "args": ["-m", "brand_registry.server"],
      "env": {
        "AWS_REGION": "eu-west-1",
        "AWS_ACCESS_KEY_ID": "${AWS_ACCESS_KEY_ID}",
        "AWS_SECRET_ACCESS_KEY": "${AWS_SECRET_ACCESS_KEY}"
      },
      "disabled": false,
      "autoApprove": [
        "search_brands",
        "get_brand_info",
        "validate_sector"
      ]
    }
  }
}
```

## Environment Variables

- `AWS_REGION`: AWS region (default: eu-west-1)
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key

## Tools

### search_brands

Search for brands in the database.

**Parameters:**
- `query` (string, required): Brand name to search for (partial match supported)
- `sector` (string, optional): Sector filter
- `limit` (integer, optional): Maximum results (default: 10)

**Example:**
```json
{
  "query": "Starbucks",
  "sector": "Food & Beverage",
  "limit": 5
}
```

**Response:**
```json
{
  "success": true,
  "count": 1,
  "brands": [
    {
      "brandid": 123,
      "brandname": "Starbucks",
      "sector": "Food & Beverage"
    }
  ]
}
```

### get_brand_info

Get detailed information about a brand.

**Parameters:**
- `brandid` (integer, required): The brand identifier

**Example:**
```json
{
  "brandid": 123
}
```

**Response:**
```json
{
  "success": true,
  "brand": {
    "brandid": 123,
    "brandname": "Starbucks",
    "sector": "Food & Beverage"
  },
  "combo_count": 1250,
  "mccid_distribution": [
    {
      "mccid": 5812,
      "mcc_desc": "Eating Places",
      "mcc_sector": "Food",
      "count": 1200
    },
    {
      "mccid": 5814,
      "mcc_desc": "Fast Food Restaurants",
      "mcc_sector": "Food",
      "count": 50
    }
  ]
}
```

### validate_sector

Validate if a sector is appropriate for a brand.

**Parameters:**
- `brandid` (integer, required): The brand identifier
- `sector` (string, required): The sector to validate

**Example:**
```json
{
  "brandid": 123,
  "sector": "Food & Beverage"
}
```

**Response:**
```json
{
  "success": true,
  "valid": true,
  "confidence": 0.96,
  "reason": "Sector aligns with 96.0% of MCCIDs",
  "current_sector": "Food & Beverage",
  "proposed_sector": "Food & Beverage",
  "mccid_sector_distribution": [
    {
      "mcc_sector": "Food",
      "count": 1200
    },
    {
      "mcc_sector": "Beverage",
      "count": 50
    }
  ]
}
```

## Testing

```bash
# Test the server
python -m brand_registry.server --help

# Run integration tests
pytest tests/integration/test_brand_registry_mcp.py
```

## Troubleshooting

### AWS Credentials Not Found

Ensure AWS credentials are configured:

```bash
# Set environment variables
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_REGION=eu-west-1

# Or use AWS CLI configuration
aws configure
```

### Athena Query Errors

- Verify the database `brand_metadata_generator_db` exists
- Check that tables (brand, combo, mcc) are accessible
- Ensure IAM permissions include Athena query execution

### Connection Timeout

- Check network connectivity to AWS
- Verify security group rules allow Athena access
- Increase timeout in client configuration

## License

Proprietary - Brand Metadata Generator Project
