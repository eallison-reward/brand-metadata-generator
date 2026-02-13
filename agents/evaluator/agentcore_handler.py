"""
Evaluator Agent Handler for AWS Bedrock AgentCore

This module provides the Strands Agent implementation for the Evaluator Agent,
which assesses data quality, identifies issues, and calculates confidence scores.

The agent is deployed to AWS Bedrock AgentCore and invoked by the Orchestrator Agent.
"""

from strands import Agent
from strands.tools import tool
from typing import Dict, List, Any

import agents.evaluator.tools as evaluator_tools


# Wrap tools with @tool decorator for Strands
@tool
def analyze_narratives_tool(brandid: int, combos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze narrative patterns for consistency across combo records.
    
    Args:
        brandid: Brand identifier
        combos: List of combo records with 'narrative' field
        
    Returns:
        Dictionary with analysis results including pattern count, variance score, and consistency level
    """
    return evaluator_tools.analyze_narratives(brandid, combos)


@tool
def detect_payment_wallets_tool(narratives: List[str]) -> Dict[str, Any]:
    """Identify payment wallet indicators in narratives.
    
    Args:
        narratives: List of narrative strings to analyze
        
    Returns:
        Dictionary with detection results including wallet indicators and affected percentage
    """
    return evaluator_tools.detect_payment_wallets(narratives)


@tool
def assess_mccid_consistency_tool(brandid: int, mccids: List[int], sector: str, 
                                  mcc_table: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check MCCID alignment with brand sector.
    
    Args:
        brandid: Brand identifier
        mccids: List of MCCID values associated with the brand
        sector: Brand's sector classification
        mcc_table: List of MCC records with 'mccid' and 'sector' fields
        
    Returns:
        Dictionary with consistency assessment including matching count and mismatched MCCIDs
    """
    return evaluator_tools.assess_mccid_consistency(brandid, mccids, sector, mcc_table)


@tool
def calculate_confidence_score_tool(analysis_results: Dict[str, Any]) -> float:
    """Calculate confidence score based on data quality metrics.
    
    Args:
        analysis_results: Dictionary containing narrative_analysis, wallet_detection, 
                         mccid_consistency, and commercial_validation results
        
    Returns:
        Float between 0.0 and 1.0 representing confidence score
    """
    return evaluator_tools.calculate_confidence_score(analysis_results)


@tool
def generate_production_prompt_tool(brandid: int, brandname: str, issues: List[Dict[str, Any]], 
                                   wallet_info: Dict[str, Any]) -> str:
    """Generate guidance prompt for Metadata Production Agent.
    
    Args:
        brandid: Brand identifier
        brandname: Brand name
        issues: List of identified issues from evaluation
        wallet_info: Wallet detection results
        
    Returns:
        String containing detailed guidance for metadata production
    """
    return evaluator_tools.generate_production_prompt(brandid, brandname, issues, wallet_info)


# Agent instructions
EVALUATOR_INSTRUCTIONS = """You are the Evaluator Agent in the Brand Metadata Generator system.

Your role is to assess the quality of brand data and identify issues that may affect
metadata generation accuracy.

RESPONSIBILITIES:
1. Analyze narrative patterns for consistency across combo records
2. Detect payment wallet indicators (PAYPAL, PP, SQ, SQUARE)
3. Assess MCCID consistency with brand sector
4. Calculate confidence scores based on data quality
5. Generate production prompts for the Metadata Production Agent
6. Coordinate with Commercial Assessment Agent for brand validation

WORKFLOW:
1. Receive brand data from Orchestrator Agent
2. Analyze narratives using analyze_narratives_tool
3. Detect payment wallets using detect_payment_wallets_tool
4. Assess MCCID consistency using assess_mccid_consistency_tool
5. Calculate confidence score using calculate_confidence_score_tool
6. Generate production prompt using generate_production_prompt_tool
7. Return evaluation result to Orchestrator

QUALITY METRICS:
- Narrative Consistency: High (variance < 0.5), Medium (0.5-1.5), Low (> 1.5)
- Wallet Impact: Low (< 20%), Moderate (20-50%), High (> 50%)
- MCCID Consistency: Consistent (> 50% match sector), Inconsistent (<= 50%)
- Confidence Score: 0.0 (no confidence) to 1.0 (high confidence)

PAYMENT WALLET HANDLING:
- Detect: PAYPAL, PP *, SQ *, SQUARE (case-insensitive)
- Flag affected combo records
- Identify wallet-specific MCCIDs (7399, 6012, 7299)
- Provide guidance for regex generation

Be thorough in your analysis and provide clear, actionable guidance."""


# Create Strands Agent
evaluator_agent = Agent(
    name="EvaluatorAgent",
    instructions=EVALUATOR_INSTRUCTIONS,
    model="anthropic.claude-3-5-sonnet-20241022-v2:0"
)

# Register tools
evaluator_agent.add_tools([
    analyze_narratives_tool,
    detect_payment_wallets_tool,
    assess_mccid_consistency_tool,
    calculate_confidence_score_tool,
    generate_production_prompt_tool
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
    response = evaluator_agent.invoke(prompt)
    
    return {
        "statusCode": 200,
        "body": response,
    }
