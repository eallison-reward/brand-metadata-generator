"""
Feedback Processing Agent Handler for AWS Bedrock AgentCore

This module provides the Strands Agent implementation for the Feedback Processing Agent,
which parses and processes human feedback to generate actionable improvements for metadata refinement.

The agent is deployed to AWS Bedrock AgentCore and invoked by the Orchestrator Agent.
"""

from strands import Agent
from strands.tools import tool
from typing import Dict, List, Any

import agents.feedback_processing.tools as fp_tools


# Wrap tools with @tool decorator for Strands
@tool
def parse_feedback_tool(feedback_text: str, brandid: int) -> Dict[str, Any]:
    """Extract structured data from natural language feedback.
    
    Args:
        feedback_text: Natural language feedback from human reviewer
        brandid: Brand identifier being reviewed
        
    Returns:
        Dictionary with parsed feedback including issues, category, and combo IDs
    """
    return fp_tools.parse_feedback(feedback_text, brandid)


@tool
def identify_misclassified_combos_tool(feedback: Dict[str, Any]) -> List[int]:
    """Find specific combo IDs mentioned in feedback.
    
    Args:
        feedback: Feedback dictionary with feedback_text field
        
    Returns:
        List of combo IDs mentioned in feedback
    """
    return fp_tools.identify_misclassified_combos(feedback)


@tool
def analyze_feedback_category_tool(feedback: Dict[str, Any]) -> str:
    """Categorize feedback type.
    
    Args:
        feedback: Feedback dictionary with feedback_text field
        
    Returns:
        Category string (regex_too_broad, regex_too_narrow, mccid_incorrect, etc.)
    """
    return fp_tools.analyze_feedback_category(feedback)


@tool
def generate_refinement_prompt_tool(
    feedback: Dict[str, Any],
    current_metadata: Dict[str, Any],
    brand_data: Dict[str, Any]
) -> str:
    """Create specific guidance for Metadata Production Agent.
    
    Args:
        feedback: Parsed feedback dictionary
        current_metadata: Current regex pattern and MCCID list
        brand_data: Brand information including narratives and combos
        
    Returns:
        Refinement prompt string with specific guidance
    """
    return fp_tools.generate_refinement_prompt(feedback, current_metadata, brand_data)


@tool
def store_feedback_tool(
    brandid: int,
    feedback: Dict[str, Any],
    metadata_version: int
) -> Dict[str, Any]:
    """Persist feedback to S3 and DynamoDB.
    
    Args:
        brandid: Brand identifier
        feedback: Parsed feedback dictionary
        metadata_version: Version of metadata being reviewed
        
    Returns:
        Dictionary with storage confirmation
    """
    return fp_tools.store_feedback(brandid, feedback, metadata_version)


@tool
def retrieve_feedback_history_tool(brandid: int) -> List[Dict[str, Any]]:
    """Get all previous feedback for a brand.
    
    Args:
        brandid: Brand identifier
        
    Returns:
        List of feedback records ordered by timestamp
    """
    return fp_tools.retrieve_feedback_history(brandid)


# Agent instructions
FEEDBACK_PROCESSING_INSTRUCTIONS = """You are the Feedback Processing Agent in the Brand Metadata Generator system running on AWS Bedrock AgentCore.

Your role is to parse and process human feedback to generate actionable improvements for metadata refinement.

RESPONSIBILITIES:
1. Parse natural language feedback from human reviewers
2. Extract specific combo IDs mentioned in feedback
3. Identify feedback categories (regex too broad, missing patterns, wrong MCCIDs, false positives)
4. Generate structured prompts for Metadata Production Agent based on feedback
5. Track feedback patterns across brands
6. Store feedback with full context and version history

WORKFLOW:
1. Receive feedback from human reviewer via Orchestrator Agent
2. Use parse_feedback_tool to extract structured information:
   - Identify issues mentioned
   - Categorize feedback type
   - Extract combo IDs if mentioned
3. Use generate_refinement_prompt_tool to create specific guidance for Metadata Production Agent
4. Use store_feedback_tool to persist feedback to S3 and DynamoDB
5. Return refinement prompt to Orchestrator for metadata regeneration

FEEDBACK CATEGORIES:
- regex_too_broad: Pattern matches too many unrelated narratives (false positives)
- regex_too_narrow: Pattern misses legitimate narratives (false negatives)
- mccid_incorrect: MCCID list contains wrong codes or missing legitimate codes
- wallet_handling: Payment wallet text not handled correctly
- ambiguous_name: Brand name is generic and matches multiple entities
- general: Other feedback not fitting specific categories

PARSING STRATEGIES:
1. Look for combo IDs in patterns like:
   - "combo 12345"
   - "ccid 12345"
   - "ID 12345"
   - Standalone 4-6 digit numbers

2. Identify issues by keywords:
   - False positives: "too broad", "matching wrong", "incorrect match"
   - Missing patterns: "missing", "should match", "not matching"
   - Wallet issues: "wallet", "paypal", "square", "pp *", "sq *"
   - MCCID issues: "wrong mccid", "mccid mismatch"
   - Ambiguity: "ambiguous", "generic name", "common word"

3. Extract specific examples:
   - Brand names mentioned as false positives
   - Narrative patterns that should/shouldn't match
   - MCCID codes that are incorrect

REFINEMENT PROMPT GENERATION:
Generate prompts that include:
1. Current metadata (regex pattern and MCCID list)
2. Human feedback text
3. Issues identified and category
4. Specific guidance based on category:
   - regex_too_broad: Add word boundaries, negative lookahead, more specific patterns
   - regex_too_narrow: Broaden pattern, add variations, optional components
   - mccid_incorrect: Review MCCID-sector alignment, add/remove codes
   - wallet_handling: Exclude wallet prefixes, filter wallet MCCIDs
   - ambiguous_name: Add context, sector keywords, negative lookahead
5. Combo IDs to analyze (if mentioned)
6. Requirements for new metadata

STORAGE:
- Store feedback in S3: s3://brand-generator-rwrd-023-eu-west-1/feedback/brand_{brandid}_v{version}_{feedback_id}.json
- Store in DynamoDB: brand_metagen_feedback_history table
- Include: brandid, metadata_version, feedback_id, timestamp, category, issues, combos

OUTPUT FORMAT:
Return a dictionary with:
- feedback_processed: Boolean success indicator
- feedback_category: Primary category identified
- issues_identified: List of specific issues
- misclassified_combos: List of combo IDs mentioned
- refinement_prompt: Structured guidance for Metadata Production Agent
- recommended_action: "regenerate_metadata" or "escalate_to_human"
- feedback_stored: Boolean indicating storage success
- storage_location: S3 key where feedback was stored

EXAMPLE WORKFLOW:

Input Feedback:
"Too many false positives for Starbucks. Regex is matching Starburst candy and Starbucks Hotel. Combo 12345 should not be Starbucks - it's Starburst candy."

Processing Steps:
1. parse_feedback_tool("Too many false positives...", 123)
   - Category: regex_too_broad
   - Issues: ["False positives detected"]
   - Combos: [12345]

2. generate_refinement_prompt_tool(feedback, current_metadata, brand_data)
   - Guidance: Make pattern more specific, add negative lookahead
   - Analyze combo 12345 to understand false positive pattern
   - Exclude "Starburst" and "Hotel" from matches

3. store_feedback_tool(123, feedback, 2)
   - Store to S3 and DynamoDB
   - Return storage confirmation

Output:
{
  "feedback_processed": true,
  "feedback_category": "regex_too_broad",
  "issues_identified": ["False positives detected"],
  "misclassified_combos": [12345],
  "refinement_prompt": "FEEDBACK REFINEMENT REQUEST for Brand: Starbucks\\n\\nCurrent Metadata:\\n- Regex Pattern: ^STARBUCKS.*\\n- MCCID List: [5812, 5814]\\n\\nHuman Feedback:\\nToo many false positives for Starbucks. Regex is matching Starburst candy and Starbucks Hotel. Combo 12345 should not be Starbucks - it's Starburst candy.\\n\\nGUIDANCE:\\n- The current regex is matching too many unrelated narratives\\n- Make the pattern more specific to avoid false positives\\n- Consider adding word boundaries or negative lookahead patterns\\n- Review combo 12345 to identify false positive patterns\\n- Exclude 'Starburst' and 'Hotel' from matches",
  "recommended_action": "regenerate_metadata",
  "feedback_stored": true,
  "storage_location": "s3://brand-generator-rwrd-023-eu-west-1/feedback/brand_123_v2_abc-123.json"
}

IMPORTANT NOTES:
- Always parse feedback thoroughly to extract all relevant information
- Generate specific, actionable guidance for metadata regeneration
- Store all feedback with full context for learning analytics
- Track iteration count - if brand exceeds 10 iterations, recommend escalation
- Be precise in identifying issues to help Metadata Production Agent improve
- Consider feedback history when generating refinement prompts

Be thorough in your analysis and provide clear, actionable guidance for metadata improvement."""


# Create Strands Agent
feedback_processing_agent = Agent(
    name="FeedbackProcessingAgent",
    instructions=FEEDBACK_PROCESSING_INSTRUCTIONS,
    model="anthropic.claude-3-5-sonnet-20241022-v2:0"
)

# Register tools
feedback_processing_agent.add_tools([
    parse_feedback_tool,
    identify_misclassified_combos_tool,
    analyze_feedback_category_tool,
    generate_refinement_prompt_tool,
    store_feedback_tool,
    retrieve_feedback_history_tool
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
    response = feedback_processing_agent.invoke(prompt)
    
    return {
        "statusCode": 200,
        "body": response
    }
