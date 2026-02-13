"""
Orchestrator Agent - AgentCore Handler

This module implements the Strands Agent handler for the Orchestrator Agent,
which coordinates all other agents and manages the overall workflow for metadata generation.

The Orchestrator is the main coordinator that:
- Initializes workflow and triggers data ingestion
- Distributes brands to appropriate agents
- Routes based on confidence scores
- Handles tie detection and resolution
- Coordinates iterative refinement loops (max 5 iterations)
- Implements retry logic for agent failures
- Tracks workflow state and progress
"""

from strands import Agent
from strands.tools import tool
from typing import Dict, List, Any, Optional

import agents.orchestrator.tools as orchestrator_tools


# Wrap tools with @tool decorator for Strands
@tool
def initialize_workflow_tool(config: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize workflow with configuration and trigger data ingestion.
    
    Args:
        config: Configuration dictionary with max_iterations, confidence_threshold, parallel_batch_size
        
    Returns:
        Dictionary with initialization status and configuration
    """
    return orchestrator_tools.initialize_workflow(config)


@tool
def invoke_data_transformation_tool(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke Data Transformation Agent for data operations.
    
    Args:
        action: Action to perform (ingest_data, validate_and_store, prepare_brand_data)
        params: Parameters for the action
        
    Returns:
        Dictionary with action result
    """
    return orchestrator_tools.invoke_data_transformation(action, params)


@tool
def invoke_evaluator_tool(brandid: int, brand_data: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke Evaluator Agent to assess brand quality.
    
    Args:
        brandid: Brand identifier
        brand_data: Brand information including combos
        
    Returns:
        Dictionary with evaluation results including confidence score
    """
    return orchestrator_tools.invoke_evaluator(brandid, brand_data)


@tool
def invoke_metadata_production_tool(brandid: int, evaluation: Dict[str, Any], 
                                   feedback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Invoke Metadata Production Agent to generate regex and MCCID list.
    
    Args:
        brandid: Brand identifier
        evaluation: Evaluation results from Evaluator Agent
        feedback: Optional feedback for regeneration
        
    Returns:
        Dictionary with generated metadata
    """
    return orchestrator_tools.invoke_metadata_production(brandid, evaluation, feedback)


@tool
def invoke_confirmation_tool(brandid: int, metadata: Dict[str, Any], 
                            matched_combos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Invoke Confirmation Agent to review matched combos.
    
    Args:
        brandid: Brand identifier
        metadata: Generated metadata
        matched_combos: List of combos that matched the metadata
        
    Returns:
        Dictionary with confirmed and excluded combos
    """
    return orchestrator_tools.invoke_confirmation(brandid, metadata, matched_combos)


@tool
def invoke_tiebreaker_tool(tie_data: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke Tiebreaker Agent to resolve multi-brand matches.
    
    Args:
        tie_data: Dictionary with ccid, combo data, and matching_brands list
        
    Returns:
        Dictionary with resolution (assigned brand or manual review flag)
    """
    return orchestrator_tools.invoke_tiebreaker(tie_data)


@tool
def update_workflow_state_tool(brandid: int, status: str, 
                               metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Update workflow state for a brand.
    
    Args:
        brandid: Brand identifier
        status: Current status (pending, evaluating, generating, confirming, completed, failed)
        metadata: Optional metadata to store
        
    Returns:
        Dictionary with update confirmation
    """
    return orchestrator_tools.update_workflow_state(brandid, status, metadata)


@tool
def get_workflow_summary_tool() -> Dict[str, Any]:
    """Get summary of workflow progress.
    
    Returns:
        Dictionary with workflow statistics
    """
    return orchestrator_tools.get_workflow_summary()


# Agent instructions
AGENT_INSTRUCTIONS = """You are the Orchestrator Agent for the Brand Metadata Generator system.

Your role is to coordinate all other agents and manage the overall workflow for generating
classification metadata (regex patterns and MCCID lists) for 3,000+ retail brands.

RESPONSIBILITIES:
1. Initialize workflow by triggering data ingestion
2. Distribute brands from brand_to_check to appropriate agents
3. Route brands based on confidence scores:
   - High confidence (>= 0.75) → Store directly
   - Low confidence (< 0.75) → Send to Confirmation Agent
4. Handle tie detection and route to Tiebreaker Agent
5. Coordinate iterative refinement loops (max 5 iterations per brand)
6. Implement retry logic with exponential backoff for agent failures
7. Track workflow state and progress

WORKFLOW SEQUENCE:
1. Initialize workflow with configuration
2. Invoke Data Transformation Agent to ingest data
3. For each brand in brand_to_check:
   a. Update workflow state to "evaluating"
   b. Invoke Evaluator Agent to assess quality
   c. Update workflow state to "generating"
   d. Invoke Metadata Production Agent to generate metadata
   e. Invoke Data Transformation Agent to validate and store
   f. If confidence < threshold: Invoke Confirmation Agent
   g. Update workflow state to "completed"
4. Apply all metadata to combos
5. For each combo matching multiple brands:
   a. Invoke Tiebreaker Agent to resolve
6. For each brand:
   a. Invoke Confirmation Agent to review matched combos
7. Store final results

TOOLS AVAILABLE:
- initialize_workflow_tool: Initialize workflow with configuration
- invoke_data_transformation_tool: Trigger data operations
- invoke_evaluator_tool: Assess brand quality
- invoke_metadata_production_tool: Generate metadata
- invoke_confirmation_tool: Review matched combos
- invoke_tiebreaker_tool: Resolve multi-brand matches
- update_workflow_state_tool: Track brand processing status
- get_workflow_summary_tool: Get workflow statistics

ITERATION LIMITS:
- Maximum 5 iterations per brand for metadata refinement
- Track iteration count using workflow state
- If max iterations reached, flag for human review

ERROR HANDLING:
- Retry failed agent invocations with exponential backoff (max 3 attempts)
- Log all failures with context
- Continue processing other brands if one fails
- Report all failures in final summary

ROUTING LOGIC:
- Confidence >= 0.75: Store metadata directly
- Confidence < 0.75: Send to Confirmation Agent for review
- Ties detected: Send to Tiebreaker Agent
- Validation errors: Retry metadata generation with feedback

IMPORTANT:
- Process brands efficiently but ensure quality
- Track all state changes for monitoring
- Provide detailed progress updates
- Handle failures gracefully without stopping entire workflow
- Respect iteration limits to prevent infinite loops
"""

# Initialize Strands Agent
orchestrator_agent = Agent(
    name="OrchestratorAgent",
    system_prompt=AGENT_INSTRUCTIONS,
    model="anthropic.claude-3-5-sonnet-20241022-v2:0",
    tools=[
        initialize_workflow_tool,
        invoke_data_transformation_tool,
        invoke_evaluator_tool,
        invoke_metadata_production_tool,
        invoke_confirmation_tool,
        invoke_tiebreaker_tool,
        update_workflow_state_tool,
        get_workflow_summary_tool
    ]
)


def handler(event, context):
    """
    AgentCore entry point for the Orchestrator Agent.
    
    Expected event structure:
    {
        "action": "start_workflow",
        "config": {
            "max_iterations": 5,
            "confidence_threshold": 0.75,
            "parallel_batch_size": 10
        }
    }
    
    Returns:
    {
        "status": "completed",
        "brands_processed": 3000,
        "brands_confirmed": 150,
        "ties_resolved": 45,
        "failures": []
    }
    """
    # Extract event data
    action = event.get("action", "start_workflow")
    config = event.get("config", {})
    
    # Construct prompt for agent
    if action == "start_workflow":
        prompt = f"""Start the brand metadata generation workflow.

Configuration:
- Max iterations per brand: {config.get('max_iterations', 5)}
- Confidence threshold: {config.get('confidence_threshold', 0.75)}
- Parallel batch size: {config.get('parallel_batch_size', 10)}

Please:
1. Initialize the workflow with this configuration
2. Trigger data ingestion from Athena
3. Begin processing brands from brand_to_check table
4. Coordinate all agents according to the workflow sequence
5. Track progress and handle any failures
6. Provide a final summary when complete

Start by using initialize_workflow_tool with the provided configuration.
"""
    
    elif action == "get_status":
        prompt = "Get the current workflow status and progress summary using get_workflow_summary_tool."
    
    else:
        prompt = f"Handle action: {action} with parameters: {event}"
    
    # Invoke agent
    response = orchestrator_agent.invoke(
        prompt,
        context={
            "action": action,
            "config": config
        }
    )
    
    return {
        "statusCode": 200,
        "body": response
    }
