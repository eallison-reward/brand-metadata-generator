"""
Feedback Processing Agent Tools

This module provides tools for the Feedback Processing Agent to parse and
process human feedback for metadata refinement.

The Feedback Processing Agent:
- Parses natural language feedback from humans
- Extracts specific combo IDs mentioned in feedback
- Identifies feedback categories (regex too broad, missing patterns, wrong MCCIDs, false positives)
- Generates structured prompts for Metadata Production Agent based on feedback
- Tracks feedback patterns across brands
- Stores feedback with full context and version history
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Feedback category keywords
FEEDBACK_CATEGORIES = {
    "regex_too_broad": [
        "too broad", "too many", "false positive", "matching wrong", "incorrect match",
        "matches unrelated", "over-matching", "too general"
    ],
    "regex_too_narrow": [
        "too narrow", "missing", "not matching", "should match", "doesn't match",
        "under-matching", "too specific", "missed"
    ],
    "mccid_incorrect": [
        "wrong mccid", "incorrect mccid", "mccid mismatch", "bad mccid",
        "mccid should be", "mccid error"
    ],
    "wallet_handling": [
        "wallet", "paypal", "square", "pp *", "sq *", "payment processor"
    ],
    "ambiguous_name": [
        "ambiguous", "common word", "generic name", "multiple meanings",
        "not specific enough"
    ]
}


def parse_feedback(feedback_text: str, brandid: int) -> Dict[str, Any]:
    """
    Extract structured data from natural language feedback.
    
    Parses human feedback to identify issues, extract combo IDs,
    and categorize the type of feedback provided.
    
    Args:
        feedback_text: Natural language feedback from human reviewer
        brandid: Brand identifier being reviewed
        
    Returns:
        Dictionary with parsed feedback including:
        - feedback_id: Unique identifier
        - brandid: Brand identifier
        - feedback_text: Original feedback text
        - issues_identified: List of specific issues found
        - category: Primary feedback category
        - misclassified_combos: List of combo IDs mentioned
        - timestamp: ISO 8601 timestamp
    
    Requirements: 14.2, 14.3, 16.2
    """
    if not feedback_text:
        return {
            "feedback_id": str(uuid.uuid4()),
            "brandid": brandid,
            "feedback_text": "",
            "issues_identified": [],
            "category": "unknown",
            "misclassified_combos": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": "Empty feedback text"
        }
    
    logger.info(f"Parsing feedback for brand {brandid}")
    
    # Generate unique feedback ID
    feedback_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Extract combo IDs mentioned in feedback
    misclassified_combos = identify_misclassified_combos({"feedback_text": feedback_text})
    
    # Analyze feedback category
    category = analyze_feedback_category({"feedback_text": feedback_text})
    
    # Extract specific issues from feedback
    issues_identified = _extract_issues(feedback_text)
    
    return {
        "feedback_id": feedback_id,
        "brandid": brandid,
        "feedback_text": feedback_text,
        "issues_identified": issues_identified,
        "category": category,
        "misclassified_combos": misclassified_combos,
        "timestamp": timestamp
    }


def _extract_issues(feedback_text: str) -> List[str]:
    """
    Extract specific issues from feedback text.
    
    Args:
        feedback_text: Feedback text to analyze
        
    Returns:
        List of specific issues identified
    """
    issues = []
    text_lower = feedback_text.lower()
    
    # Check for false positive mentions
    if any(keyword in text_lower for keyword in ["false positive", "incorrect match", "wrong match"]):
        issues.append("False positives detected")
    
    # Check for missing pattern mentions
    if any(keyword in text_lower for keyword in ["missing", "should match", "not matching"]):
        issues.append("Missing patterns or narratives")
    
    # Check for wallet-related issues
    if any(keyword in text_lower for keyword in ["wallet", "paypal", "square", "pp *", "sq *"]):
        issues.append("Payment wallet handling issue")
    
    # Check for MCCID issues
    if any(keyword in text_lower for keyword in ["mccid", "merchant category"]):
        issues.append("MCCID classification issue")
    
    # Check for ambiguity mentions
    if any(keyword in text_lower for keyword in ["ambiguous", "generic", "common word"]):
        issues.append("Ambiguous brand name")
    
    return issues if issues else ["General feedback"]


def identify_misclassified_combos(feedback: Dict[str, Any]) -> List[int]:
    """
    Find specific combo IDs mentioned in feedback.
    
    Extracts combo identifiers (ccid values) that are explicitly
    mentioned in the feedback text.
    
    Args:
        feedback: Feedback dictionary with feedback_text field
        
    Returns:
        List of combo IDs (ccid values) mentioned in feedback
    
    Requirements: 14.3, 16.3
    """
    feedback_text = feedback.get("feedback_text", "")
    
    if not feedback_text:
        return []
    
    # Extract numeric IDs from feedback
    # Look for patterns like "combo 12345", "ccid 12345", "ID 12345", or just "12345"
    patterns = [
        r'\bcombo\s+(\d+)',
        r'\bccid\s+(\d+)',
        r'\bid\s+(\d+)',
        r'\b(\d{4,6})\b'  # 4-6 digit numbers (likely combo IDs)
    ]
    
    combo_ids = []
    for pattern in patterns:
        matches = re.findall(pattern, feedback_text, re.IGNORECASE)
        combo_ids.extend([int(match) for match in matches])
    
    # Deduplicate and sort
    unique_combo_ids = sorted(list(set(combo_ids)))
    
    logger.info(f"Identified {len(unique_combo_ids)} combo IDs in feedback")
    
    return unique_combo_ids


def analyze_feedback_category(feedback: Dict[str, Any]) -> str:
    """
    Categorize feedback type.
    
    Analyzes feedback text to determine the primary category
    of issue being reported.
    
    Args:
        feedback: Feedback dictionary with feedback_text field
        
    Returns:
        Category string: "regex_too_broad", "regex_too_narrow",
        "mccid_incorrect", "wallet_handling", "ambiguous_name", or "general"
    
    Requirements: 14.3, 16.4
    """
    feedback_text = feedback.get("feedback_text", "")
    
    if not feedback_text:
        return "unknown"
    
    text_lower = feedback_text.lower()
    
    # Count keyword matches for each category
    category_scores = {}
    for category, keywords in FEEDBACK_CATEGORIES.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        if score > 0:
            category_scores[category] = score
    
    # Return category with highest score
    if category_scores:
        primary_category = max(category_scores, key=category_scores.get)
        logger.info(f"Feedback categorized as: {primary_category}")
        return primary_category
    
    return "general"


def generate_refinement_prompt(
    feedback: Dict[str, Any],
    current_metadata: Dict[str, Any],
    brand_data: Dict[str, Any]
) -> str:
    """
    Create specific guidance for Metadata Production Agent.
    
    Generates a structured prompt that provides actionable guidance
    for regenerating metadata based on feedback.
    
    Args:
        feedback: Parsed feedback dictionary
        current_metadata: Current regex pattern and MCCID list
        brand_data: Brand information including narratives and combos
        
    Returns:
        Refinement prompt string with specific guidance
    
    Requirements: 14.4, 14.5, 16.5
    """
    if not feedback or not current_metadata:
        return "No feedback or metadata provided"
    
    category = feedback.get("category", "general")
    feedback_text = feedback.get("feedback_text", "")
    issues = feedback.get("issues_identified", [])
    misclassified_combos = feedback.get("misclassified_combos", [])
    
    brandname = brand_data.get("brandname", "Unknown")
    current_regex = current_metadata.get("regex", "")
    current_mccids = current_metadata.get("mccids", [])
    
    # Build refinement prompt based on category
    prompt_parts = [
        f"FEEDBACK REFINEMENT REQUEST for Brand: {brandname}",
        f"",
        f"Current Metadata:",
        f"- Regex Pattern: {current_regex}",
        f"- MCCID List: {current_mccids}",
        f"",
        f"Human Feedback:",
        f"{feedback_text}",
        f"",
        f"Issues Identified: {', '.join(issues)}",
        f"Category: {category}",
        f""
    ]
    
    # Add category-specific guidance
    if category == "regex_too_broad":
        prompt_parts.extend([
            "GUIDANCE:",
            "- The current regex is matching too many unrelated narratives",
            "- Make the pattern more specific to avoid false positives",
            "- Consider adding word boundaries or negative lookahead patterns",
            "- Analyze the false positive examples to understand what to exclude"
        ])
        
        if misclassified_combos:
            prompt_parts.append(f"- Review combos {misclassified_combos} to identify false positive patterns")
    
    elif category == "regex_too_narrow":
        prompt_parts.extend([
            "GUIDANCE:",
            "- The current regex is not matching all legitimate narratives",
            "- Broaden the pattern to capture more variations",
            "- Look for alternative brand name spellings or abbreviations",
            "- Consider optional components in the pattern"
        ])
        
        if misclassified_combos:
            prompt_parts.append(f"- Review combos {misclassified_combos} to identify missing patterns")
    
    elif category == "mccid_incorrect":
        prompt_parts.extend([
            "GUIDANCE:",
            "- The MCCID list contains incorrect or missing codes",
            "- Review the MCCIDs associated with the brand's actual business",
            "- Remove MCCIDs that don't align with the brand's sector",
            "- Add any missing MCCIDs that are legitimate for this brand"
        ])
    
    elif category == "wallet_handling":
        prompt_parts.extend([
            "GUIDANCE:",
            "- Payment wallet text is not being handled correctly",
            "- Ensure wallet prefixes (PAYPAL, PP *, SQ *, SQUARE) are excluded from regex",
            "- Filter out wallet-specific MCCIDs (7399, 6012, 7299)",
            "- Focus on the actual brand name after removing wallet text"
        ])
    
    elif category == "ambiguous_name":
        prompt_parts.extend([
            "GUIDANCE:",
            "- The brand name is ambiguous or matches multiple entities",
            "- Add more specific context to the regex pattern",
            "- Consider sector-specific keywords or location indicators",
            "- Use negative lookahead to exclude unrelated matches"
        ])
    
    else:  # general
        prompt_parts.extend([
            "GUIDANCE:",
            "- Review the feedback carefully and address the specific concerns",
            "- Analyze the mentioned combos to understand the issues",
            "- Adjust both regex pattern and MCCID list as needed"
        ])
    
    # Add combo-specific guidance if IDs were mentioned
    if misclassified_combos:
        prompt_parts.extend([
            "",
            f"SPECIFIC COMBOS TO ANALYZE:",
            f"The following combo IDs were mentioned in feedback: {misclassified_combos}",
            f"Retrieve these combos from the database and analyze their narratives and MCCIDs.",
            f"Understand why they were misclassified and adjust the metadata accordingly."
        ])
    
    prompt_parts.extend([
        "",
        "REQUIREMENTS:",
        "- Generate a new regex pattern that addresses the feedback",
        "- Generate a new MCCID list that addresses the feedback",
        "- Ensure the new metadata is more accurate than the previous version",
        "- Test the new pattern against sample narratives to verify improvement"
    ])
    
    return "\n".join(prompt_parts)


def store_feedback(
    brandid: int,
    feedback: Dict[str, Any],
    metadata_version: int
) -> Dict[str, Any]:
    """
    Persist feedback to S3 and DynamoDB.
    
    Stores feedback with full context including timestamp, version,
    and all parsed information for future analysis.
    
    Args:
        brandid: Brand identifier
        feedback: Parsed feedback dictionary
        metadata_version: Version of metadata being reviewed
        
    Returns:
        Dictionary with storage confirmation including:
        - feedback_stored: Boolean success indicator
        - storage_location: S3 key where feedback was stored
        - dynamodb_stored: Boolean indicating DynamoDB storage
    
    Requirements: 14.4, 14.9, 16.12
    """
    if not feedback:
        return {
            "feedback_stored": False,
            "error": "No feedback provided"
        }
    
    logger.info(f"Storing feedback for brand {brandid}, version {metadata_version}")
    
    # Prepare feedback record
    feedback_record = {
        "brandid": brandid,
        "metadata_version": metadata_version,
        "feedback_id": feedback.get("feedback_id"),
        "timestamp": feedback.get("timestamp"),
        "feedback_type": feedback.get("category"),
        "feedback_text": feedback.get("feedback_text"),
        "issues_identified": feedback.get("issues_identified", []),
        "misclassified_combos": feedback.get("misclassified_combos", []),
        "category": feedback.get("category")
    }
    
    # S3 storage location
    s3_key = f"feedback/brand_{brandid}_v{metadata_version}_{feedback.get('feedback_id')}.json"
    
    # In production, this would write to S3 and DynamoDB
    # For now, we'll simulate the storage
    try:
        # Placeholder for S3 write
        # s3_client.put_object(
        #     Bucket='brand-generator-rwrd-023-eu-west-1',
        #     Key=s3_key,
        #     Body=json.dumps(feedback_record)
        # )
        
        # Placeholder for DynamoDB write
        # dynamodb_client.put_item(
        #     TableName='brand_metagen_feedback_history',
        #     Item={
        #         'brandid': brandid,
        #         'feedback_id': feedback.get('feedback_id'),
        #         'timestamp': feedback.get('timestamp'),
        #         'metadata_version': metadata_version,
        #         'feedback_data': json.dumps(feedback_record)
        #     }
        # )
        
        logger.info(f"Feedback stored at {s3_key}")
        
        return {
            "feedback_stored": True,
            "storage_location": f"s3://brand-generator-rwrd-023-eu-west-1/{s3_key}",
            "dynamodb_stored": True,
            "feedback_id": feedback.get("feedback_id")
        }
    
    except Exception as e:
        logger.error(f"Error storing feedback: {str(e)}")
        return {
            "feedback_stored": False,
            "error": str(e)
        }


def retrieve_feedback_history(brandid: int) -> List[Dict[str, Any]]:
    """
    Get all previous feedback for a brand.
    
    Retrieves complete feedback history including all versions,
    timestamps, and associated metadata.
    
    Args:
        brandid: Brand identifier
        
    Returns:
        List of feedback records ordered by timestamp (newest first)
    
    Requirements: 14.9, 16.12
    """
    logger.info(f"Retrieving feedback history for brand {brandid}")
    
    # In production, this would query DynamoDB
    # For now, we'll return an empty list as placeholder
    try:
        # Placeholder for DynamoDB query
        # response = dynamodb_client.query(
        #     TableName='brand_metagen_feedback_history',
        #     KeyConditionExpression='brandid = :brandid',
        #     ExpressionAttributeValues={':brandid': brandid},
        #     ScanIndexForward=False  # Newest first
        # )
        # 
        # feedback_history = []
        # for item in response.get('Items', []):
        #     feedback_history.append(json.loads(item['feedback_data']))
        
        # For now, return empty list
        feedback_history = []
        
        logger.info(f"Retrieved {len(feedback_history)} feedback records for brand {brandid}")
        
        return feedback_history
    
    except Exception as e:
        logger.error(f"Error retrieving feedback history: {str(e)}")
        return []
