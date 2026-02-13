"""
Metadata Production Agent Handler for AWS Bedrock AgentCore

Generates regex patterns and MCCID lists based on evaluator findings and feedback.
"""

from strands import Agent
from strands.tools import tool
from typing import Dict, List, Any

import agents.metadata_production.tools as mp_tools


@tool
def generate_regex_tool(brandid: int, narratives: List[str], guidance: str = "") -> str:
    """Generate regex pattern for narrative matching."""
    return mp_tools.generate_regex(brandid, narratives, guidance)


@tool
def generate_mccid_list_tool(brandid: int, mccids: List[int], guidance: str = "") -> List[int]:
    """Generate list of legitimate MCCIDs for a brand."""
    return mp_tools.generate_mccid_list(brandid, mccids, guidance)


@tool
def filter_wallet_text_tool(narratives: List[str], wallet_indicators: List[str]) -> List[str]:
    """Remove wallet text from narratives."""
    return mp_tools.filter_wallet_text(narratives, wallet_indicators)


@tool
def validate_pattern_coverage_tool(regex: str, narratives: List[str]) -> Dict[str, Any]:
    """Test regex against sample narratives."""
    return mp_tools.validate_pattern_coverage(regex, narratives)


METADATA_PRODUCTION_INSTRUCTIONS = """You are the Metadata Production Agent in the Brand Metadata Generator system.

Your role is to generate regex patterns and MCCID lists for brand classification.

RESPONSIBILITIES:
1. Generate regex patterns for narrative matching
2. Generate lists of legitimate MCCIDs
3. Exclude payment wallet text from patterns
4. Incorporate feedback for iterative refinement
5. Validate pattern coverage

WORKFLOW:
1. Receive brand data and evaluation from Orchestrator
2. Use filter_wallet_text_tool to clean narratives if wallets detected
3. Use generate_regex_tool to create regex pattern
4. Use generate_mccid_list_tool to create MCCID list
5. Use validate_pattern_coverage_tool to test pattern
6. Return metadata with coverage statistics

PATTERN GENERATION GUIDELINES:
- Focus on brand name variations
- Exclude wallet prefixes (PAYPAL, PP *, SQ *, SQUARE)
- Use case-insensitive matching
- Allow for common suffixes (store numbers, etc.)
- Aim for 90%+ coverage with <5% false positives

Be thorough and generate accurate patterns."""


metadata_production_agent = Agent(
    name="MetadataProductionAgent",
    instructions=METADATA_PRODUCTION_INSTRUCTIONS,
    model="anthropic.claude-3-5-sonnet-20241022-v2:0"
)

metadata_production_agent.add_tools([
    generate_regex_tool,
    generate_mccid_list_tool,
    filter_wallet_text_tool,
    validate_pattern_coverage_tool
])


def handler(event, context):
    """AgentCore entry point."""
    prompt = event.get("prompt", "")
    response = metadata_production_agent.invoke(prompt)
    return {"statusCode": 200, "body": response}
