"""Data Transformation Agent for AWS Bedrock AgentCore."""

from strands import Agent
from strands.tools import tool

from agents.data_transformation.tools import DataTransformationTools

# Initialize tools
tools_instance = DataTransformationTools()

# Define tools for Strands agent
@tool
def query_athena(table_name: str, columns: str = "*", where: str = None, limit: int = None) -> dict:
    """Query Athena table and return results.
    
    Args:
        table_name: Name of table (brand, brand_to_check, combo, mcc)
        columns: Columns to select (default: all)
        where: Optional WHERE clause without WHERE keyword
        limit: Optional row limit
        
    Returns:
        Dictionary with query results
    """
    return tools_instance.query_athena(table_name, columns, where, limit)


@tool
def validate_foreign_keys() -> dict:
    """Validate foreign key relationships between tables.
    
    Returns:
        Dictionary with validation results and any issues found
    """
    return tools_instance.validate_foreign_keys()


@tool
def validate_regex(pattern: str) -> dict:
    """Validate regex pattern syntax.
    
    Args:
        pattern: Regex pattern to validate
        
    Returns:
        Dictionary indicating if pattern is valid
    """
    return tools_instance.validate_regex(pattern)


@tool
def validate_mccids(mccid_list: list[int]) -> dict:
    """Validate that MCCIDs exist in mcc table.
    
    Args:
        mccid_list: List of MCCID values to check
        
    Returns:
        Dictionary with validation results
    """
    return tools_instance.validate_mccids(mccid_list)


@tool
def write_to_s3(brandid: int, metadata: dict) -> dict:
    """Write brand metadata to S3.
    
    Args:
        brandid: Brand ID
        metadata: Metadata dictionary to store
        
    Returns:
        Dictionary with write result including S3 key
    """
    return tools_instance.write_to_s3(brandid, metadata)


@tool
def read_from_s3(brandid: int) -> dict:
    """Read brand metadata from S3.
    
    Args:
        brandid: Brand ID
        
    Returns:
        Dictionary with metadata if found
    """
    return tools_instance.read_from_s3(brandid)


@tool
def prepare_brand_data(brandid: int) -> dict:
    """Aggregate all data for a brand including combos, MCCIDs, and narratives.
    
    Args:
        brandid: Brand ID
        
    Returns:
        Dictionary with complete brand data
    """
    return tools_instance.prepare_brand_data(brandid)


@tool
def apply_metadata_to_combos(brandid: int, regex_pattern: str, mccid_list: list[int]) -> dict:
    """Apply metadata (regex and MCCIDs) to all combos and return matches.
    
    Args:
        brandid: Brand ID that owns this metadata
        regex_pattern: Regex pattern for narrative matching
        mccid_list: List of valid MCCIDs
        
    Returns:
        Dictionary with all matched combos
    """
    return tools_instance.apply_metadata_to_combos(brandid, regex_pattern, mccid_list)


# Initialize Strands agent
agent = Agent(
    name="DataTransformationAgent",
    instructions="""You are the Data Transformation Agent for the Brand Metadata Generator system.

Your responsibilities:
1. Query data from AWS Athena database (brand_metadata_generator_db)
2. Validate data integrity (foreign keys, regex patterns, MCCIDs)
3. Store and retrieve brand metadata from S3
4. Prepare brand data for other agents
5. Apply metadata to combos to find matches

Available tables in Athena:
- brand: brandid, brandname, sector
- brand_to_check: brandid (brands requiring metadata generation)
- combo: ccid, mid, brandid, mccid, narrative
- mcc: mccid, mcc_desc, sector

When querying data:
- Use appropriate WHERE clauses to filter results
- Use LIMIT for large result sets
- Handle errors gracefully and report them

When validating:
- Check regex syntax before storing
- Verify MCCIDs exist in mcc table
- Validate foreign key relationships

When storing metadata:
- Include all required fields (regex, mccids, confidence_score, etc.)
- Use consistent JSON structure
- Store in S3 with key format: metadata/brand_{brandid}.json

Always return structured responses with success status and relevant data.""",
    model="anthropic.claude-3-5-sonnet-20241022-v2:0",
)

# Register tools
agent.add_tools([
    query_athena,
    validate_foreign_keys,
    validate_regex,
    validate_mccids,
    write_to_s3,
    read_from_s3,
    prepare_brand_data,
    apply_metadata_to_combos,
])


# Handler function for AgentCore
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
    response = agent.invoke(prompt)
    
    return {
        "statusCode": 200,
        "body": response,
    }
