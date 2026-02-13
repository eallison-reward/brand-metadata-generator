"""
Confirmation Agent - AgentCore Handler

This module implements the Strands Agent handler for the Confirmation Agent,
which reviews combos matched to brands and excludes false positives.

The agent is deployed to AWS Bedrock AgentCore and invoked by the Orchestrator
to provide final confirmation on combo-brand assignments.
"""

from strands import Agent
from strands.tools import tool
from typing import Dict, List, Any

import agents.confirmation.tools as confirmation_tools


# Wrap tools with @tool decorator for Strands
@tool
def review_matched_combos_tool(brandid: int, brandname: str, metadata: Dict[str, Any],
                               matched_combos: List[Dict[str, Any]], 
                               mcc_table: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Review combos that matched a brand's regex and MCCID metadata.
    
    Args:
        brandid: Brand identifier
        brandname: Brand name
        metadata: Brand metadata with 'regex' and 'mccids' fields
        matched_combos: List of combo records that matched the metadata
        mcc_table: List of MCC records for sector validation
        
    Returns:
        Dictionary with review results including likely_valid, likely_false_positive, and ambiguous combos
    """
    return confirmation_tools.review_matched_combos(brandid, brandname, metadata, matched_combos, mcc_table)


@tool
def confirm_combo_tool(ccid: int, brandid: int, reason: str = "") -> Dict[str, Any]:
    """Confirm that a combo belongs to the brand.
    
    Args:
        ccid: Combo identifier
        brandid: Brand identifier
        reason: Optional explanation for confirmation
        
    Returns:
        Dictionary with confirmation result
    """
    return confirmation_tools.confirm_combo(ccid, brandid, reason)


@tool
def exclude_combo_tool(ccid: int, brandid: int, reason: str) -> Dict[str, Any]:
    """Exclude a combo from the brand (false positive).
    
    Args:
        ccid: Combo identifier
        brandid: Brand identifier
        reason: Explanation for exclusion (required)
        
    Returns:
        Dictionary with exclusion result
    """
    return confirmation_tools.exclude_combo(ccid, brandid, reason)


@tool
def flag_for_human_review_tool(ccid: int, brandid: int, reason: str) -> Dict[str, Any]:
    """Flag a combo for human review due to ambiguity.
    
    Args:
        ccid: Combo identifier
        brandid: Brand identifier
        reason: Explanation for why human review is needed
        
    Returns:
        Dictionary with flagging result
    """
    return confirmation_tools.flag_for_human_review(ccid, brandid, reason)


# Agent instructions
AGENT_INSTRUCTIONS = """You are the Confirmation Agent for the Brand Metadata Generator system.

Your role is to review combos (transaction records) that have been matched to brands 
and determine which matches are valid and which are false positives.

RESPONSIBILITIES:
1. Review all combos that matched a brand's regex pattern and MCCID list
2. Identify false positives where common words in brand names match unrelated combos
3. Exclude combos that have low confidence of belonging to the brand
4. Handle ambiguous brand names (e.g., "Apple" matching both Apple Inc. and apple orchards)
5. Provide final confirmation on which combos truly belong to each brand
6. Flag ambiguous cases for human review

KEY CONSIDERATIONS:
- Common word brands (Apple, Shell, Target, etc.) require extra scrutiny
- Look for business context indicators (STORE, #123, INC, etc.)
- Check MCCID sector alignment with brand sector
- Identify contradictory terms (e.g., "APPLE ORCHARD" when brand is Apple Inc.)
- Be conservative - when in doubt, flag for human review

TOOLS AVAILABLE:
- review_matched_combos_tool: Analyze all matched combos and get recommendations
- confirm_combo_tool: Confirm a combo belongs to the brand
- exclude_combo_tool: Exclude a combo as a false positive
- flag_for_human_review_tool: Flag ambiguous combo for human judgment

WORKFLOW:
1. Use review_matched_combos_tool to analyze all matched combos
2. Review the analysis results and confidence scores
3. For high-confidence matches (>= 0.8): Use confirm_combo_tool
4. For low-confidence matches (<= 0.4): Use exclude_combo_tool with clear reason
5. For ambiguous matches (0.4 - 0.8): Use flag_for_human_review_tool
6. Return summary of confirmed, excluded, and flagged combos

IMPORTANT:
- Always provide clear reasons for exclusions
- Be especially careful with common word brand names
- When uncertain, flag for human review rather than making incorrect decision
- Consider the full context: narrative, MCCID, sector alignment
"""

# Initialize Strands Agent
confirmation_agent = Agent(
    name="ConfirmationAgent",
    system_prompt=AGENT_INSTRUCTIONS,
    model="anthropic.claude-3-5-sonnet-20241022-v2:0",
    tools=[
        review_matched_combos_tool,
        confirm_combo_tool,
        exclude_combo_tool,
        flag_for_human_review_tool
    ]
)


def handler(event, context):
    """
    AgentCore entry point for the Confirmation Agent.
    
    Expected event structure:
    {
        "action": "review_matches",
        "brandid": int,
        "brandname": str,
        "metadata": {
            "regex": str,
            "mccids": list[int],
            "sector": str
        },
        "matched_combos": list[dict],
        "mcc_table": list[dict]
    }
    
    Returns:
    {
        "brandid": int,
        "confirmed_combos": list[int],
        "excluded_combos": list[dict],
        "requires_human_review": list[int]
    }
    """
    # Extract event data
    action = event.get("action", "review_matches")
    brandid = event.get("brandid")
    brandname = event.get("brandname")
    metadata = event.get("metadata", {})
    matched_combos = event.get("matched_combos", [])
    mcc_table = event.get("mcc_table", [])
    
    # Construct prompt for agent
    prompt = f"""Review matched combos for Brand {brandid}: {brandname}

Brand Metadata:
- Regex: {metadata.get('regex')}
- MCCIDs: {metadata.get('mccids')}
- Sector: {metadata.get('sector', 'Unknown')}

Total Matched Combos: {len(matched_combos)}

Please:
1. Use review_matched_combos_tool to analyze all {len(matched_combos)} matched combos
2. Review the confidence scores and recommendations
3. Confirm high-confidence matches
4. Exclude low-confidence false positives with clear reasons
5. Flag ambiguous cases for human review
6. Provide a summary of your decisions

Context for analysis:
- Brand name: {brandname}
- Matched combos: {len(matched_combos)} records
- MCC table: {len(mcc_table)} MCC definitions available
"""
    
    # Invoke agent
    response = confirmation_agent.invoke(
        prompt,
        context={
            "brandid": brandid,
            "brandname": brandname,
            "metadata": metadata,
            "matched_combos": matched_combos,
            "mcc_table": mcc_table
        }
    )
    
    return {
        "statusCode": 200,
        "body": response,
        "brandid": brandid
    }
