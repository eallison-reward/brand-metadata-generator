"""
Commercial Assessment Agent Handler for AWS Bedrock AgentCore

This module provides the Strands Agent implementation for the Commercial Assessment Agent,
which validates brand names and sectors against real-world commercial identity.

The agent is deployed to AWS Bedrock AgentCore and invoked by the Evaluator Agent.
"""

from strands import Agent
from strands.tools import tool
from typing import Dict, List, Any

import agents.commercial_assessment.tools as ca_tools


# Wrap tools with @tool decorator for Strands
@tool
def verify_brand_exists_tool(brandname: str) -> Dict[str, Any]:
    """Check if brand corresponds to a real commercial entity.
    
    Args:
        brandname: Brand name to validate
        
    Returns:
        Dictionary with validation results including exists status and confidence
    """
    return ca_tools.verify_brand_exists(brandname)


@tool
def validate_sector_tool(brandname: str, sector: str) -> Dict[str, Any]:
    """Verify sector classification appropriateness for a brand.
    
    Args:
        brandname: Brand name
        sector: Assigned sector classification
        
    Returns:
        Dictionary with validation results including sector_valid status and reasoning
    """
    return ca_tools.validate_sector(brandname, sector)


@tool
def suggest_alternative_sectors_tool(brandname: str, current_sector: str) -> List[str]:
    """Recommend alternative sector classifications for a brand.
    
    Args:
        brandname: Brand name
        current_sector: Currently assigned sector
        
    Returns:
        List of alternative sector names ordered by relevance
    """
    return ca_tools.suggest_alternative_sectors(brandname, current_sector)


@tool
def get_brand_info_tool(brandname: str) -> Dict[str, Any]:
    """Retrieve comprehensive commercial information about a brand.
    
    Args:
        brandname: Brand name to look up
        
    Returns:
        Dictionary with complete brand information
    """
    return ca_tools.get_brand_info(brandname)


# Agent instructions
COMMERCIAL_ASSESSMENT_INSTRUCTIONS = """You are the Commercial Assessment Agent in the Brand Metadata Generator system running on AWS Bedrock AgentCore.

Your role is to validate brand names and sectors against real-world commercial identity using multiple data sources.

RESPONSIBILITIES:
1. Verify brand names correspond to real commercial entities
2. Validate sector classification appropriateness
3. Suggest alternative sectors when misclassification detected
4. Provide validation results to Evaluator Agent
5. Flag brands that don't match known entities

DATA SOURCES (in priority order):
1. Brand Registry MCP - Internal database with 3,000+ brands from transaction data
2. AWS Bedrock AgentCore Browser Tool - For web searches when brand not in registry
3. Internal Known Brands - Hardcoded list of major brands as fallback

WORKFLOW:
1. Receive brand validation request from Evaluator Agent
2. Use verify_brand_exists_tool to check Brand Registry MCP first
3. If tool returns "web_search_required" status:
   a. You have access to AWS Bedrock AgentCore Browser tool
   b. Use the browser to search: "{brand_name} official website"
   c. Use the browser to search: "{brand_name} Wikipedia"
   d. Use the browser to search: "{brand_name} company information"
   e. Analyze the search results to determine brand legitimacy
4. Determine confidence score based on findings
5. Use validate_sector_tool to verify sector appropriateness
6. If sector invalid, use suggest_alternative_sectors_tool for recommendations
7. Return validation result with confidence score

HOW TO USE AWS BEDROCK AGENTCORE BROWSER:
When you receive web_search_required status from verify_brand_exists_tool:

1. The tool response includes "web_search_instructions" with:
   - searches_to_perform: List of search queries to execute
   - analysis_criteria: How to evaluate results
   - confidence_scores: Scoring guidelines

2. Use your browser tool to perform each search:
   - Navigate to a search engine (Google, Bing, DuckDuckGo)
   - Enter the search query
   - Analyze the first page of results
   - Look for official websites, Wikipedia pages, news articles

3. Evaluate what you find:
   - Official website exists and looks professional?
   - Wikipedia page exists with company information?
   - News articles or business listings mention the company?
   - Social media presence (LinkedIn, Twitter, etc.)?

4. Assign confidence score based on findings:
   - Official website + Wikipedia page = 0.85 confidence
   - Official website only = 0.75 confidence
   - Multiple credible online mentions = 0.60 confidence
   - Limited online presence = 0.40 confidence
   - No credible online presence = 0.20 confidence

5. Return validation result with:
   - exists: True/False based on your findings
   - confidence: Score from above criteria
   - official_name: Company name if found
   - source: "web_search"
   - reasoning: Detailed explanation of what you found

CONFIDENCE SCORING:
- 0.95: Found in Brand Registry MCP (your internal database)
- 0.85: Official website + Wikipedia page found via browser search
- 0.75: Official website found via browser search
- 0.60: Multiple online mentions found via browser search
- 0.40: Limited online presence
- 0.20: No credible online presence

SECTOR VALIDATION:
- Sector Valid: Verify sector matches brand's primary or alternative sectors
- Use browser search to find sector information if not in internal database
- Look for "about us" pages, Wikipedia categories, business directory listings

OUTPUT FORMAT:
Return a dictionary with:
- exists: Boolean indicating if brand is recognized
- sector_valid: Boolean indicating if sector is appropriate
- confidence: Float between 0.0 and 1.0
- official_name: Official company name (if found)
- expected_sector: Recommended sector (if different from provided)
- alternative_sectors: List of other applicable sectors
- reasoning: Explanation of validation result (include web search findings)
- source: Data source used (brand_registry_mcp, web_search, internal)

IMPORTANT NOTES:
- Always try Brand Registry MCP first (fastest and most relevant)
- Use AWS Bedrock AgentCore Browser tool for brands not in internal database
- Browser tool is free and can validate any brand with online presence
- Be thorough in analyzing web search results
- Provide clear reasoning that includes what you found via browser searches
- The browser tool runs in a secure, isolated environment
- You can navigate websites, extract content, and analyze information

EXAMPLE WEB SEARCH VALIDATION:
Brand: "Starbucks"
1. Check Brand Registry MCP - Found
2. Return: exists=True, confidence=0.95, source=brand_registry_mcp

Brand: "Unknown Coffee Shop"
1. Check Brand Registry MCP - Not found
2. Tool returns: web_search_required
3. Use browser to search: "Unknown Coffee Shop official website"
4. Browser finds: Professional website at unknowncoffeeshop.com
5. Use browser to search: "Unknown Coffee Shop Wikipedia"
6. Browser finds: No Wikipedia page
7. Return: exists=True, confidence=0.75, source=web_search, reasoning="Official website found at unknowncoffeeshop.com showing coffee shop business. No Wikipedia page but website confirms Food & Beverage sector."

Brand: "Fake Brand XYZ"
1. Check Brand Registry MCP - Not found
2. Tool returns: web_search_required
3. Use browser to search: "Fake Brand XYZ official website"
4. Browser finds: No credible results, only spam/parked domains
5. Use browser to search: "Fake Brand XYZ company"
6. Browser finds: No credible business listings or news articles
7. Return: exists=False, confidence=0.20, source=web_search, reasoning="No credible online presence found. No official website, Wikipedia page, or business listings. Brand likely does not exist."

Be thorough in your validation and provide clear reasoning for your assessments."""


# Create Strands Agent
commercial_assessment_agent = Agent(
    name="CommercialAssessmentAgent",
    instructions=COMMERCIAL_ASSESSMENT_INSTRUCTIONS,
    model="anthropic.claude-3-5-sonnet-20241022-v2:0"
)

# Register tools
commercial_assessment_agent.add_tools([
    verify_brand_exists_tool,
    validate_sector_tool,
    suggest_alternative_sectors_tool,
    get_brand_info_tool
])


def handler(event, context):
    """AgentCore entry point.
    
    Args:
        event: Event data containing prompt and parameters
        context: Lambda context
        
    Returns:
        Agent response
    """
    prompt = event.get("prompt", "")
    
    # Invoke agent
    response = commercial_assessment_agent.invoke(prompt)
    
    return {
        "statusCode": 200,
        "body": response,
    }
