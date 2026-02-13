"""
Tiebreaker Agent - AgentCore Handler

This module implements the Strands Agent handler for the Tiebreaker Agent,
which resolves scenarios where a combo matches multiple brands.

The agent is deployed to AWS Bedrock AgentCore and invoked by the Orchestrator
to resolve tie situations.
"""

from strands import Agent
from strands.tools import tool
from typing import Dict, List, Any

import agents.tiebreaker.tools as tiebreaker_tools


# Wrap tools with @tool decorator for Strands
@tool
def resolve_multi_match_tool(ccid: int, matching_brands: List[Dict[str, Any]], 
                             combo_data: Dict[str, Any]) -> Dict[str, Any]:
    """Determine which brand a combo most likely belongs to when it matches multiple brands.
    
    Args:
        ccid: Combo identifier
        matching_brands: List of brands that matched this combo
        combo_data: Combo information with 'narrative', 'mccid', 'mid'
        
    Returns:
        Dictionary with resolution including assigned brand or manual review flag
    """
    return tiebreaker_tools.resolve_multi_match(ccid, matching_brands, combo_data)


@tool
def analyze_narrative_similarity_tool(narrative: str, brand_names: List[str]) -> Dict[str, Any]:
    """Compare narrative text to brand names to determine similarity.
    
    Args:
        narrative: Transaction narrative text
        brand_names: List of brand names to compare against
        
    Returns:
        Dictionary with similarity scores for each brand
    """
    return tiebreaker_tools.analyze_narrative_similarity(narrative, brand_names)


@tool
def compare_mccid_alignment_tool(mccid: int, brands: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check MCCID fit for each brand to determine which is most appropriate.
    
    Args:
        mccid: The MCCID to check
        brands: List of brand dictionaries with metadata
        
    Returns:
        Dictionary with alignment scores for each brand
    """
    return tiebreaker_tools.compare_mccid_alignment(mccid, brands)


@tool
def calculate_match_confidence_tool(ccid: int, brandid: int, 
                                   narrative: str, brand_data: Dict[str, Any]) -> float:
    """Calculate confidence score for a specific combo-brand match.
    
    Args:
        ccid: Combo identifier
        brandid: Brand identifier
        narrative: Transaction narrative
        brand_data: Brand information including metadata
        
    Returns:
        Float between 0.0 and 1.0 representing confidence
    """
    return tiebreaker_tools.calculate_match_confidence(ccid, brandid, narrative, brand_data)


# Agent instructions
AGENT_INSTRUCTIONS = """You are the Tiebreaker Agent for the Brand Metadata Generator system.

Your role is to resolve scenarios where a combo (transaction record) matches multiple brands'
regex patterns and MCCID lists. You must determine which brand the combo most likely belongs to.

RESPONSIBILITIES:
1. Analyze combos that matched multiple brands' metadata
2. Determine which brand the combo most likely belongs to
3. Consider narrative text patterns, MCCID alignment, and brand characteristics
4. Assign combo to the most appropriate brand with confidence score
5. Flag combos that cannot be resolved with high confidence for human review

KEY CONSIDERATIONS:
- More specific brand names usually win (e.g., "Shell Station" vs "Shell")
- Narrative similarity is the strongest signal
- MCCID position in brand's list indicates priority
- Longer, more specific regex patterns indicate more targeted brands
- When confidence is low (<0.7) or margin is small (<0.2), flag for human review

TOOLS AVAILABLE:
- resolve_multi_match_tool: Main resolution tool that analyzes all factors
- analyze_narrative_similarity_tool: Compare narrative to brand names
- compare_mccid_alignment_tool: Check MCCID fit for each brand
- calculate_match_confidence_tool: Calculate confidence for specific match

WORKFLOW:
1. Use resolve_multi_match_tool to analyze the tie situation
2. Review the confidence score and reasoning
3. If confidence >= 0.7 and clear winner: Assign to that brand
4. If confidence < 0.7 or close scores: Flag for human review
5. Always provide clear reasoning for your decision

DECISION THRESHOLDS:
- High confidence: >= 0.7 with margin >= 0.2 → Assign to best brand
- Low confidence: < 0.7 or margin < 0.2 → Flag for human review
- Single brand: Only one match → Assign immediately

IMPORTANT:
- Be conservative - when in doubt, flag for human review
- Provide detailed reasoning for all decisions
- Consider all factors: narrative, MCCID, pattern specificity
- More specific patterns (longer regex, specific brand names) should win ties
"""

# Initialize Strands Agent
tiebreaker_agent = Agent(
    name="TiebreakerAgent",
    system_prompt=AGENT_INSTRUCTIONS,
    model="anthropic.claude-3-5-sonnet-20241022-v2:0",
    tools=[
        resolve_multi_match_tool,
        analyze_narrative_similarity_tool,
        compare_mccid_alignment_tool,
        calculate_match_confidence_tool
    ]
)


def handler(event, context):
    """
    AgentCore entry point for the Tiebreaker Agent.
    
    Expected event structure:
    {
        "action": "resolve_tie",
        "ccid": int,
        "combo": {
            "narrative": str,
            "mccid": int,
            "mid": str
        },
        "matching_brands": list[dict]
    }
    
    Returns:
    {
        "ccid": int,
        "resolution_type": "single_brand" or "manual_review",
        "assigned_brandid": int or None,
        "confidence": float,
        "reasoning": str
    }
    """
    # Extract event data
    action = event.get("action", "resolve_tie")
    ccid = event.get("ccid")
    combo = event.get("combo", {})
    matching_brands = event.get("matching_brands", [])
    
    # Construct prompt for agent
    brand_names = [b.get("brandname", "Unknown") for b in matching_brands]
    
    prompt = f"""Resolve tie for Combo {ccid}

Combo Details:
- Narrative: {combo.get('narrative')}
- MCCID: {combo.get('mccid')}
- MID: {combo.get('mid')}

Matching Brands ({len(matching_brands)}):
"""
    
    for i, brand in enumerate(matching_brands, 1):
        prompt += f"\n{i}. {brand.get('brandname')} (ID: {brand.get('brandid')})"
        prompt += f"\n   - Sector: {brand.get('sector')}"
        prompt += f"\n   - Regex: {brand.get('metadata', {}).get('regex')}"
        prompt += f"\n   - MCCIDs: {brand.get('metadata', {}).get('mccids')}"
    
    prompt += f"""

Please:
1. Use resolve_multi_match_tool to analyze this tie
2. Review the confidence scores and reasoning
3. Make a decision: assign to best brand or flag for human review
4. Provide clear reasoning for your decision

Remember:
- High confidence (>=0.7) with clear margin (>=0.2) → Assign
- Low confidence or close scores → Flag for human review
- More specific brand names and patterns should win
"""
    
    # Invoke agent
    response = tiebreaker_agent.invoke(
        prompt,
        context={
            "ccid": ccid,
            "combo": combo,
            "matching_brands": matching_brands
        }
    )
    
    return {
        "statusCode": 200,
        "body": response,
        "ccid": ccid
    }
