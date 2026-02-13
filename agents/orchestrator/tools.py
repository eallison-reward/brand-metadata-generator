"""
Orchestrator Agent - Tools Module

This module implements tools for the Orchestrator Agent, which coordinates
all other agents and manages the overall workflow for metadata generation.

The Orchestrator is responsible for:
- Initializing workflow and triggering data ingestion
- Distributing brands to appropriate agents
- Routing based on confidence scores
- Handling tie detection and resolution
- Coordinating iterative refinement loops
- Implementing retry logic for agent failures
- Tracking workflow state and progress
"""

import logging
from typing import Dict, List, Any, Optional
import time
import json

logger = logging.getLogger(__name__)


class WorkflowState:
    """Manages workflow state for brand processing."""
    
    def __init__(self):
        self.brands_status = {}  # brandid -> status dict
        self.iteration_counts = {}  # brandid -> iteration count
        self.failures = []  # List of failure records
        
    def update_brand_status(self, brandid: int, status: str, metadata: Optional[Dict] = None):
        """Update status for a brand."""
        self.brands_status[brandid] = {
            "status": status,
            "metadata": metadata,
            "updated_at": time.time()
        }
        
    def increment_iteration(self, brandid: int) -> int:
        """Increment and return iteration count for a brand."""
        current = self.iteration_counts.get(brandid, 0)
        self.iteration_counts[brandid] = current + 1
        return self.iteration_counts[brandid]
    
    def get_iteration_count(self, brandid: int) -> int:
        """Get current iteration count for a brand."""
        return self.iteration_counts.get(brandid, 0)
    
    def add_failure(self, brandid: int, error: str, agent: str):
        """Record a failure."""
        self.failures.append({
            "brandid": brandid,
            "error": error,
            "agent": agent,
            "timestamp": time.time()
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get workflow summary statistics."""
        statuses = {}
        for brand_info in self.brands_status.values():
            status = brand_info["status"]
            statuses[status] = statuses.get(status, 0) + 1
            
        return {
            "brands_processed": len(self.brands_status),
            "status_breakdown": statuses,
            "total_failures": len(self.failures),
            "average_iterations": sum(self.iteration_counts.values()) / len(self.iteration_counts) if self.iteration_counts else 0
        }


# Global workflow state (in production, this would be in DynamoDB)
_workflow_state = WorkflowState()


def initialize_workflow(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initialize workflow by loading configuration and triggering data ingestion.
    
    Args:
        config: Configuration dictionary with:
            - max_iterations: Maximum iterations per brand (default: 5)
            - confidence_threshold: Threshold for automatic approval (default: 0.75)
            - parallel_batch_size: Number of brands to process in parallel (default: 10)
            
    Returns:
        Dictionary with initialization status and configuration
    """
    try:
        # Set defaults
        max_iterations = config.get("max_iterations", 5)
        confidence_threshold = config.get("confidence_threshold", 0.75)
        parallel_batch_size = config.get("parallel_batch_size", 10)
        
        logger.info(f"Initializing workflow with config: {config}")
        
        # Reset workflow state
        global _workflow_state
        _workflow_state = WorkflowState()
        
        # Validate configuration
        if max_iterations < 1 or max_iterations > 10:
            return {
                "success": False,
                "error": "max_iterations must be between 1 and 10"
            }
            
        if confidence_threshold < 0.0 or confidence_threshold > 1.0:
            return {
                "success": False,
                "error": "confidence_threshold must be between 0.0 and 1.0"
            }
            
        if parallel_batch_size < 1 or parallel_batch_size > 100:
            return {
                "success": False,
                "error": "parallel_batch_size must be between 1 and 100"
            }
        
        return {
            "success": True,
            "config": {
                "max_iterations": max_iterations,
                "confidence_threshold": confidence_threshold,
                "parallel_batch_size": parallel_batch_size
            },
            "workflow_initialized": True,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Workflow initialization failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def invoke_data_transformation(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke Data Transformation Agent for data operations.
    
    Args:
        action: Action to perform ("ingest_data", "validate_and_store", "prepare_brand_data")
        params: Parameters for the action
        
    Returns:
        Dictionary with action result
    """
    try:
        logger.info(f"Invoking Data Transformation Agent: action={action}, params={params}")
        
        # In production, this would invoke the actual agent via Bedrock
        # For now, return mock response based on action
        
        if action == "ingest_data":
            return {
                "success": True,
                "status": "data_ingested",
                "brands_to_process": params.get("expected_brands", 3000),
                "total_combos": params.get("expected_combos", 150000),
                "data_quality": {
                    "missing_foreign_keys": 0,
                    "invalid_records": 0
                }
            }
            
        elif action == "validate_and_store":
            brandid = params.get("brandid")
            metadata = params.get("metadata", {})
            
            # Simulate validation
            validation_errors = []
            if not metadata.get("regex"):
                validation_errors.append("Missing regex pattern")
            if not metadata.get("mccids"):
                validation_errors.append("Missing MCCID list")
                
            if validation_errors:
                return {
                    "success": False,
                    "brandid": brandid,
                    "validation_errors": validation_errors
                }
                
            return {
                "success": True,
                "brandid": brandid,
                "s3_key": f"metadata/brand_{brandid}.json",
                "validation_errors": []
            }
            
        elif action == "prepare_brand_data":
            brandid = params.get("brandid")
            return {
                "success": True,
                "brandid": brandid,
                "brand_data": {
                    "brandname": f"Brand {brandid}",
                    "sector": "Retail",
                    "combos": []
                }
            }
            
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
            
    except Exception as e:
        logger.error(f"Data Transformation invocation failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def invoke_evaluator(brandid: int, brand_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke Evaluator Agent to assess brand quality.
    
    Args:
        brandid: Brand identifier
        brand_data: Brand information including combos
        
    Returns:
        Dictionary with evaluation results including confidence score
    """
    try:
        logger.info(f"Invoking Evaluator Agent for brand {brandid}")
        
        # In production, this would invoke the actual agent via Bedrock
        # For now, return mock evaluation
        
        return {
            "success": True,
            "brandid": brandid,
            "confidence_score": 0.85,
            "issues": [],
            "wallet_affected": False,
            "ties_detected": [],
            "production_prompt": "Generate standard metadata for this brand."
        }
        
    except Exception as e:
        logger.error(f"Evaluator invocation failed: {e}", exc_info=True)
        _workflow_state.add_failure(brandid, str(e), "Evaluator")
        return {
            "success": False,
            "brandid": brandid,
            "error": str(e)
        }


def invoke_metadata_production(brandid: int, evaluation: Dict[str, Any], 
                               feedback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Invoke Metadata Production Agent to generate regex and MCCID list.
    
    Args:
        brandid: Brand identifier
        evaluation: Evaluation results from Evaluator Agent
        feedback: Optional feedback for regeneration
        
    Returns:
        Dictionary with generated metadata
    """
    try:
        iteration = _workflow_state.get_iteration_count(brandid) + 1
        logger.info(f"Invoking Metadata Production Agent for brand {brandid}, iteration {iteration}")
        
        # In production, this would invoke the actual agent via Bedrock
        # For now, return mock metadata
        
        return {
            "success": True,
            "brandid": brandid,
            "regex": f"^BRAND{brandid}.*",
            "mccids": [5812, 5814],
            "coverage": {
                "narratives_matched": 0.95,
                "false_positives": 0.02
            },
            "iteration": iteration
        }
        
    except Exception as e:
        logger.error(f"Metadata Production invocation failed: {e}", exc_info=True)
        _workflow_state.add_failure(brandid, str(e), "MetadataProduction")
        return {
            "success": False,
            "brandid": brandid,
            "error": str(e)
        }


def invoke_confirmation(brandid: int, metadata: Dict[str, Any], 
                       matched_combos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Invoke Confirmation Agent to review matched combos.
    
    Args:
        brandid: Brand identifier
        metadata: Generated metadata
        matched_combos: List of combos that matched the metadata
        
    Returns:
        Dictionary with confirmed and excluded combos
    """
    try:
        logger.info(f"Invoking Confirmation Agent for brand {brandid}")
        
        # In production, this would invoke the actual agent via Bedrock
        # For now, return mock confirmation
        
        return {
            "success": True,
            "brandid": brandid,
            "confirmed_combos": [c["ccid"] for c in matched_combos],
            "excluded_combos": [],
            "requires_human_review": []
        }
        
    except Exception as e:
        logger.error(f"Confirmation invocation failed: {e}", exc_info=True)
        _workflow_state.add_failure(brandid, str(e), "Confirmation")
        return {
            "success": False,
            "brandid": brandid,
            "error": str(e)
        }


def invoke_tiebreaker(tie_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke Tiebreaker Agent to resolve multi-brand matches.
    
    Args:
        tie_data: Dictionary with:
            - ccid: Combo identifier
            - combo: Combo data (narrative, mccid, mid)
            - matching_brands: List of brands that matched
            
    Returns:
        Dictionary with resolution (assigned brand or manual review flag)
    """
    try:
        ccid = tie_data.get("ccid")
        logger.info(f"Invoking Tiebreaker Agent for combo {ccid}")
        
        # In production, this would invoke the actual agent via Bedrock
        # For now, return mock resolution
        
        matching_brands = tie_data.get("matching_brands", [])
        if not matching_brands:
            return {
                "success": False,
                "error": "No matching brands provided"
            }
            
        # Assign to first brand (mock logic)
        return {
            "success": True,
            "ccid": ccid,
            "resolution_type": "single_brand",
            "assigned_brandid": matching_brands[0].get("brandid"),
            "confidence": 0.85,
            "reasoning": "Mock resolution - assigned to first matching brand"
        }
        
    except Exception as e:
        logger.error(f"Tiebreaker invocation failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def update_workflow_state(brandid: int, status: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Update workflow state for a brand.
    
    Args:
        brandid: Brand identifier
        status: Current status ("pending", "evaluating", "generating", "confirming", "completed", "failed")
        metadata: Optional metadata to store
        
    Returns:
        Dictionary with update confirmation
    """
    try:
        logger.info(f"Updating workflow state: brand={brandid}, status={status}")
        
        _workflow_state.update_brand_status(brandid, status, metadata)
        
        return {
            "success": True,
            "brandid": brandid,
            "status": status,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Workflow state update failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def get_workflow_summary() -> Dict[str, Any]:
    """
    Get summary of workflow progress.
    
    Returns:
        Dictionary with workflow statistics
    """
    try:
        summary = _workflow_state.get_summary()
        summary["failures"] = _workflow_state.failures
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get workflow summary: {e}", exc_info=True)
        return {
            "error": str(e)
        }


def retry_with_backoff(func, max_retries: int = 3, initial_delay: float = 1.0):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        
    Returns:
        Function result or raises last exception
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                logger.error(f"All {max_retries} attempts failed")
                
    raise last_exception
