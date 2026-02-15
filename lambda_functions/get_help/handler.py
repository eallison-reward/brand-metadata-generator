"""Lambda handler for get_help tool.

This tool provides detailed instructions for using other tools in the system.
It helps keep the main agent prompt minimal while providing comprehensive guidance on demand.
"""

from typing import Any, Dict

from shared.utils.base_handler import BaseToolHandler
from shared.utils.error_handler import UserInputError


class GetHelpHandler(BaseToolHandler):
    """Handler for get_help tool."""
    
    def __init__(self):
        """Initialize handler."""
        super().__init__("get_help")
    
    def handle(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Override handle to return direct response format for Bedrock Agent.
        
        Args:
            event: Lambda event dictionary
            context: Lambda context object
            
        Returns:
            Direct response dictionary (not wrapped in success/data)
        """
        try:
            # Extract parameters directly from event
            parameters = event if isinstance(event, dict) else {}
            
            # Validate parameters
            self.validate_parameters(parameters)
            
            # Execute tool logic
            result = self.execute(parameters)
            
            # Return direct result (not wrapped)
            return result
            
        except Exception as e:
            # Log the error and re-raise
            self.logger.error(f"Handler error: {e}")
            raise
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate input parameters.
        
        Args:
            parameters: Input parameters
            
        Raises:
            UserInputError: If parameters are invalid
        """
        if "tool_name" not in parameters:
            raise UserInputError(
                "Parameter 'tool_name' is required",
                suggestion="Provide the name of the tool you need help with (e.g., 'query_brands_to_check')",
            )
        
        tool_name = parameters["tool_name"]
        if not isinstance(tool_name, str):
            raise UserInputError(
                f"Parameter 'tool_name' must be a string, got {type(tool_name).__name__}",
                suggestion="Provide a tool name as a string",
            )
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute help lookup for the specified tool.
        
        Args:
            parameters: Validated input parameters
                - tool_name (required): Name of the tool to get help for
            
        Returns:
            Dictionary containing detailed help information
        """
        tool_name = parameters["tool_name"]
        
        # Tool help database
        tool_help = {
            "query_brands_to_check": {
                "description": "Query brands that need processing from the DynamoDB table",
                "when_to_use": [
                    "User asks about brands or unprocessed brands",
                    "User wants to see what brands are available",
                    "User asks 'show me brands' or similar"
                ],
                "parameters": {
                    "status": {
                        "type": "string",
                        "required": False,
                        "description": "Filter by brand status",
                        "examples": ["unprocessed", "processing", "completed", "failed"]
                    },
                    "limit": {
                        "type": "integer", 
                        "required": False,
                        "description": "Maximum number of results (default: 10, max: 1000)",
                        "examples": [5, 10, 50]
                    }
                },
                "examples": [
                    "Show unprocessed brands: {\"status\": \"unprocessed\", \"limit\": 10}",
                    "Show all brands: {\"limit\": 20}",
                    "Show processing brands: {\"status\": \"processing\"}"
                ]
            },
            
            "start_workflow": {
                "description": "Start Step Functions workflows to process brands",
                "when_to_use": [
                    "User wants to process a specific brand",
                    "User says 'process brand X' or 'start workflow'",
                    "User wants to generate metadata for brands"
                ],
                "parameters": {
                    "brandid": {
                        "type": "integer or array",
                        "required": True,
                        "description": "Brand ID(s) to process",
                        "examples": [12345, [12345, 67890]]
                    },
                    "execution_name": {
                        "type": "string",
                        "required": False,
                        "description": "Optional custom name for the workflow execution",
                        "examples": ["daily-batch", "manual-process"]
                    }
                },
                "examples": [
                    "Process single brand: {\"brandid\": 12345}",
                    "Process multiple brands: {\"brandid\": [12345, 67890]}",
                    "Process with custom name: {\"brandid\": 12345, \"execution_name\": \"urgent-fix\"}"
                ]
            },
            
            "check_workflow_status": {
                "description": "Check the status of a Step Functions workflow execution",
                "when_to_use": [
                    "User asks about workflow status",
                    "User provides an execution ARN",
                    "User wants to check if processing is complete"
                ],
                "parameters": {
                    "execution_arn": {
                        "type": "string",
                        "required": True,
                        "description": "Step Functions execution ARN (returned by start_workflow)",
                        "examples": ["arn:aws:states:eu-west-1:123456789012:execution:brand-workflow:exec-abc123"]
                    }
                },
                "examples": [
                    "Check status: {\"execution_arn\": \"arn:aws:states:eu-west-1:123456789012:execution:brand-workflow:exec-abc123\"}"
                ]
            },
            
            "submit_feedback": {
                "description": "Submit user feedback about brand metadata",
                "when_to_use": [
                    "User reports issues with metadata",
                    "User suggests corrections",
                    "User provides feedback on regex or categories"
                ],
                "parameters": {
                    "brandid": {
                        "type": "integer",
                        "required": True,
                        "description": "Brand ID for the feedback",
                        "examples": [12345]
                    },
                    "feedback_text": {
                        "type": "string",
                        "required": True,
                        "description": "User's feedback description",
                        "examples": ["The regex is too broad", "Should be in Food & Beverage sector"]
                    },
                    "metadata_version": {
                        "type": "integer",
                        "required": False,
                        "description": "Specific metadata version (default: latest)",
                        "examples": [1, 2]
                    }
                },
                "examples": [
                    "Submit feedback: {\"brandid\": 12345, \"feedback_text\": \"The regex matches too many unrelated transactions\"}",
                    "Version-specific feedback: {\"brandid\": 12345, \"feedback_text\": \"Category is wrong\", \"metadata_version\": 2}"
                ]
            },
            
            "query_metadata": {
                "description": "Retrieve brand metadata details from S3 storage",
                "when_to_use": [
                    "User asks for metadata for a specific brand",
                    "User wants to see regex, MCCIDs, or confidence scores",
                    "User asks 'what's the metadata for brand X?'"
                ],
                "parameters": {
                    "brandid": {
                        "type": "integer",
                        "required": True,
                        "description": "Brand ID to retrieve metadata for",
                        "examples": [12345]
                    },
                    "version": {
                        "type": "string or integer",
                        "required": False,
                        "description": "Metadata version ('latest' or version number)",
                        "examples": ["latest", 1, 2]
                    }
                },
                "examples": [
                    "Get latest metadata: {\"brandid\": 12345}",
                    "Get specific version: {\"brandid\": 12345, \"version\": 2}"
                ]
            },
            
            "execute_athena_query": {
                "description": "Execute custom queries on the system data",
                "when_to_use": [
                    "User wants complex data analysis",
                    "User asks for brands by criteria (confidence, category)",
                    "User needs custom SQL queries"
                ],
                "parameters": {
                    "query_type": {
                        "type": "string",
                        "required": True,
                        "description": "Type of query to execute",
                        "examples": ["brands_by_confidence", "brands_by_category", "recent_workflows", "custom"]
                    },
                    "parameters": {
                        "type": "object",
                        "required": True,
                        "description": "Query-specific parameters (varies by query_type)",
                        "examples": [
                            {"min_confidence": 0.5, "max_confidence": 1.0},
                            {"sector": "Food & Beverage"},
                            {"sql": "SELECT * FROM brand WHERE sector = 'Retail'"}
                        ]
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum results (default: 10)",
                        "examples": [10, 50]
                    }
                },
                "examples": [
                    "Brands by confidence: {\"query_type\": \"brands_by_confidence\", \"parameters\": {\"min_confidence\": 0.8}}",
                    "Brands by category: {\"query_type\": \"brands_by_category\", \"parameters\": {\"sector\": \"Retail\"}}"
                ]
            },
            
            "list_escalations": {
                "description": "List brands awaiting human review",
                "when_to_use": [
                    "User asks about escalations or reviews needed",
                    "User wants to see what needs attention",
                    "User asks 'what needs review?'"
                ],
                "parameters": {
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum results (default: 10)",
                        "examples": [5, 10, 20]
                    },
                    "sort_by": {
                        "type": "string",
                        "required": False,
                        "description": "Sort field (default: escalated_at)",
                        "examples": ["escalated_at", "confidence_score", "brandid"]
                    }
                },
                "examples": [
                    "List escalations: {\"limit\": 10}",
                    "Sort by confidence: {\"sort_by\": \"confidence_score\", \"limit\": 5}"
                ]
            },
            
            "get_workflow_stats": {
                "description": "Get system performance statistics",
                "when_to_use": [
                    "User asks about system health or performance",
                    "User wants workflow statistics",
                    "User asks 'how is the system doing?'"
                ],
                "parameters": {
                    "time_period": {
                        "type": "string",
                        "required": True,
                        "description": "Time period for statistics",
                        "examples": ["last_hour", "last_day", "last_week"]
                    },
                    "include_details": {
                        "type": "boolean",
                        "required": False,
                        "description": "Include detailed execution records (default: false)",
                        "examples": [True, False]
                    }
                },
                "examples": [
                    "Daily stats: {\"time_period\": \"last_day\"}",
                    "Detailed weekly stats: {\"time_period\": \"last_week\", \"include_details\": true}"
                ]
            }
        }
        
        if tool_name not in tool_help:
            available_tools = list(tool_help.keys())
            return {
                "found": False,
                "tool_name": tool_name,
                "message": f"Tool '{tool_name}' not found",
                "available_tools": available_tools,
                "suggestion": f"Try one of these tools: {', '.join(available_tools)}"
            }
        
        help_info = tool_help[tool_name]
        
        return {
            "found": True,
            "tool_name": tool_name,
            "description": help_info["description"],
            "when_to_use": help_info["when_to_use"],
            "parameters": help_info["parameters"],
            "examples": help_info["examples"],
            "usage_tip": f"Use this tool when: {', '.join(help_info['when_to_use'][:2])}"
        }


# Lambda handler entry point
handler_instance = GetHelpHandler()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point.
    
    Args:
        event: Lambda event dictionary
        context: Lambda context object
        
    Returns:
        Standardized response dictionary
    """
    return handler_instance.handle(event, context)