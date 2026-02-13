"""
Brand Registry MCP Server Implementation

This module implements an MCP server that provides access to the brand database
stored in AWS Athena. It exposes tools for searching brands, retrieving brand
information, and validating sector classifications.
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Import Athena client
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from shared.storage.athena_client import AthenaClient


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize Athena client
athena_client = AthenaClient(
    database="brand_metadata_generator_db",
    region="eu-west-1"
)


# Create MCP server
app = Server("brand-registry")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="search_brands",
            description="Search for brands in the internal database by name or sector",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Brand name to search for (partial match supported)"
                    },
                    "sector": {
                        "type": "string",
                        "description": "Optional sector filter (e.g., 'Food & Beverage', 'Retail')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_brand_info",
            description="Get detailed information about a specific brand by brandid",
            inputSchema={
                "type": "object",
                "properties": {
                    "brandid": {
                        "type": "integer",
                        "description": "The unique brand identifier"
                    }
                },
                "required": ["brandid"]
            }
        ),
        Tool(
            name="validate_sector",
            description="Validate if a sector classification is appropriate for a brand",
            inputSchema={
                "type": "object",
                "properties": {
                    "brandid": {
                        "type": "integer",
                        "description": "The brand identifier to validate"
                    },
                    "sector": {
                        "type": "string",
                        "description": "The sector to validate (e.g., 'Food & Beverage')"
                    }
                },
                "required": ["brandid", "sector"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "search_brands":
            result = await search_brands(
                query=arguments["query"],
                sector=arguments.get("sector"),
                limit=arguments.get("limit", 10)
            )
        elif name == "get_brand_info":
            result = await get_brand_info(
                brandid=arguments["brandid"]
            )
        elif name == "validate_sector":
            result = await validate_sector(
                brandid=arguments["brandid"],
                sector=arguments["sector"]
            )
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    except Exception as e:
        logger.error(f"Error calling tool {name}: {str(e)}")
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)}, indent=2)
        )]


async def search_brands(query: str, sector: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """
    Search for brands by name.
    
    Args:
        query: Brand name to search for (partial match)
        sector: Optional sector filter
        limit: Maximum number of results
        
    Returns:
        Dictionary with search results
    """
    try:
        # Build SQL query
        sql = f"""
        SELECT 
            brandid,
            brandname,
            sector
        FROM brand
        WHERE LOWER(brandname) LIKE LOWER('%{query}%')
        """
        
        if sector:
            sql += f" AND LOWER(sector) = LOWER('{sector}')"
        
        sql += f" LIMIT {limit}"
        
        # Execute query
        results = athena_client.execute_query(sql)
        
        return {
            "success": True,
            "count": len(results),
            "brands": results
        }
    
    except Exception as e:
        logger.error(f"Error searching brands: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "brands": []
        }


async def get_brand_info(brandid: int) -> Dict[str, Any]:
    """
    Get detailed information about a brand.
    
    Args:
        brandid: The brand identifier
        
    Returns:
        Dictionary with brand information
    """
    try:
        # Get brand details
        brand_sql = f"""
        SELECT 
            brandid,
            brandname,
            sector
        FROM brand
        WHERE brandid = {brandid}
        """
        
        brand_results = athena_client.execute_query(brand_sql)
        
        if not brand_results:
            return {
                "success": False,
                "error": f"Brand {brandid} not found"
            }
        
        brand = brand_results[0]
        
        # Get combo count
        combo_sql = f"""
        SELECT COUNT(*) as combo_count
        FROM combo
        WHERE brandid = {brandid}
        """
        
        combo_results = athena_client.execute_query(combo_sql)
        combo_count = combo_results[0]["combo_count"] if combo_results else 0
        
        # Get MCCID distribution
        mccid_sql = f"""
        SELECT 
            c.mccid,
            m.mcc_desc,
            m.sector as mcc_sector,
            COUNT(*) as count
        FROM combo c
        LEFT JOIN mcc m ON c.mccid = m.mccid
        WHERE c.brandid = {brandid}
        GROUP BY c.mccid, m.mcc_desc, m.sector
        ORDER BY count DESC
        """
        
        mccid_results = athena_client.execute_query(mccid_sql)
        
        return {
            "success": True,
            "brand": brand,
            "combo_count": combo_count,
            "mccid_distribution": mccid_results
        }
    
    except Exception as e:
        logger.error(f"Error getting brand info: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def validate_sector(brandid: int, sector: str) -> Dict[str, Any]:
    """
    Validate if a sector classification is appropriate for a brand.
    
    Args:
        brandid: The brand identifier
        sector: The sector to validate
        
    Returns:
        Dictionary with validation result
    """
    try:
        # Get brand's current sector
        brand_sql = f"""
        SELECT 
            brandid,
            brandname,
            sector as current_sector
        FROM brand
        WHERE brandid = {brandid}
        """
        
        brand_results = athena_client.execute_query(brand_sql)
        
        if not brand_results:
            return {
                "success": False,
                "error": f"Brand {brandid} not found"
            }
        
        brand = brand_results[0]
        current_sector = brand["current_sector"]
        
        # Check if proposed sector matches current sector
        exact_match = current_sector.lower() == sector.lower()
        
        # Get MCCID sector distribution
        mccid_sql = f"""
        SELECT 
            m.sector as mcc_sector,
            COUNT(*) as count
        FROM combo c
        LEFT JOIN mcc m ON c.mccid = m.mccid
        WHERE c.brandid = {brandid}
        GROUP BY m.sector
        ORDER BY count DESC
        """
        
        mccid_results = athena_client.execute_query(mccid_sql)
        
        # Calculate sector alignment
        total_combos = sum(r["count"] for r in mccid_results)
        sector_matches = sum(
            r["count"] for r in mccid_results 
            if r["mcc_sector"] and r["mcc_sector"].lower() == sector.lower()
        )
        
        alignment_percentage = (sector_matches / total_combos) if total_combos > 0 else 0.0
        
        # Determine validation result
        if exact_match:
            valid = True
            confidence = 1.0
            reason = "Sector matches current classification"
        elif alignment_percentage >= 0.7:
            valid = True
            confidence = alignment_percentage
            reason = f"Sector aligns with {alignment_percentage:.1%} of MCCIDs"
        elif alignment_percentage >= 0.4:
            valid = True
            confidence = alignment_percentage
            reason = f"Sector partially aligns with {alignment_percentage:.1%} of MCCIDs"
        else:
            valid = False
            confidence = alignment_percentage
            reason = f"Sector only aligns with {alignment_percentage:.1%} of MCCIDs"
        
        return {
            "success": True,
            "valid": valid,
            "confidence": round(confidence, 3),
            "reason": reason,
            "current_sector": current_sector,
            "proposed_sector": sector,
            "mccid_sector_distribution": mccid_results
        }
    
    except Exception as e:
        logger.error(f"Error validating sector: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
