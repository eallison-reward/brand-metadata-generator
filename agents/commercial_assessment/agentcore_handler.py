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
COMMERCIAL_ASSESSMENT_INSTRUCTIONS = """You are the Commercial Assessment Agent in the Brand Metadata Generator system.

Your role is to validate brand names and sectors against real-world commercial identity.

RESPONSIBILITIES:
1. Verify brand names correspond to real commercial entities
2. Validate sector classification appropriateness
3. Suggest alternative sectors when misclassification detected
4. Provide validation results to Evaluator Agent
5. Flag brands that don't match known entities

WORKFLOW:
1. Receive brand validation request from Evaluator Agent
2. Use verify_brand_exists_tool to check if brand is real
3. Use validate_sector_tool to verify sector appropriateness
4. If sector invalid, use suggest_alternative_sectors_tool for recommendations
5. Use get_brand_info_tool to retrieve comprehensive brand information
6. Return validation result with confidence score

VALIDATION CRITERIA:
- Brand Exists: Check against known brands database
- Sector Valid: Verify sector matches brand's primary or alternative sectors
- Confidence Score: 0.0 (no confidence) to 1.0 (high confidence)

CURRENT LIMITATIONS:
- This implementation uses an internal known brands database
- Task 17 will add MCP integration for external brand databases (Crunchbase, custom registry)
- MCP integration will significantly improve validation accuracy and coverage

OUTPUT FORMAT:
Return a dictionary with:
- exists: Boolean indicating if brand is recognized
- sector_valid: Boolean indicating if sector is appropriate
- confidence: Float between 0.0 and 1.0
- official_name: Official company name (if found)
- expected_sector: Recommended sector (if different from provided)
- alternative_sectors: List of other applicable sectors
- reasoning: Explanation of validation result

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
