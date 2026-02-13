# AWS Bedrock AgentCore Browser Solution for Commercial Validation

## Summary

The Commercial Assessment Agent now uses **AWS Bedrock AgentCore Browser tool** for brand validation. This is a built-in, free browser automation capability that allows agents to search the web and validate brands.

## Critical Clarification

**Previous Misunderstanding:** The initial solution was designed for Kiro IDE's web search capabilities.

**Reality:** The agents run in **AWS Bedrock AgentCore runtime**, not Kiro IDE. AgentCore has its own built-in Browser tool that agents can use.

## What is AWS Bedrock AgentCore Browser?

AWS Bedrock AgentCore Browser is a fully managed, cloud-based browser runtime that enables AI agents to:
- Navigate websites
- Perform web searches
- Extract content from web pages
- Interact with web elements
- Analyze search results

### Key Features

✅ **Free** - No additional cost beyond AgentCore usage
✅ **Secure** - Runs in isolated, containerized environment
✅ **Managed** - No infrastructure to maintain
✅ **Integrated** - Works seamlessly with Strands Agents
✅ **Observable** - Includes live view and session recording

## How It Works

### Architecture

```
Commercial Assessment Agent (Strands)
    ↓
verify_brand_exists_tool()
    ↓
Brand Registry MCP (check internal database)
    ↓
If not found → Return "web_search_required"
    ↓
Agent uses AWS Bedrock AgentCore Browser
    ↓
Navigate to Google/Bing
    ↓
Search for brand information
    ↓
Analyze results (official website, Wikipedia, etc.)
    ↓
Return validation result with confidence score
```

### Workflow

1. **Agent receives brand validation request**
   - Brand name and sector from Evaluator Agent

2. **Check Brand Registry MCP first**
   - Call `verify_brand_exists_tool(brandname)`
   - If found in registry → Return immediately (confidence: 0.95)
   - If not found → Tool returns `web_search_required` status

3. **Agent uses Browser tool for web search**
   - Tool response includes `web_search_instructions` with:
     - List of searches to perform
     - Analysis criteria
     - Confidence scoring guidelines
   
4. **Agent performs web searches**
   - Navigate to search engine (Google, Bing, DuckDuckGo)
   - Search: "{brand_name} official website"
   - Search: "{brand_name} Wikipedia"
   - Search: "{brand_name} company information"

5. **Agent analyzes search results**
   - Look for official websites (not spam/parked domains)
   - Check for Wikipedia pages with company info
   - Find news articles or business listings
   - Verify social media presence

6. **Agent assigns confidence score**
   - Official website + Wikipedia = 0.85
   - Official website only = 0.75
   - Multiple mentions = 0.60
   - Limited presence = 0.40
   - No presence = 0.20

7. **Agent returns validation result**
   - Include findings from browser searches
   - Provide clear reasoning
   - Specify confidence score

## Implementation Details

### Updated Files

1. **agents/commercial_assessment/tools.py**
   - Added `web_search_brand()` function
   - Returns instructions for agent to perform web search
   - Updated `verify_brand_exists()` to return `web_search_required` status

2. **agents/commercial_assessment/agentcore_handler.py**
   - Updated agent instructions with Browser tool usage
   - Added detailed examples of browser search workflow
   - Included confidence scoring guidelines

3. **infrastructure/prompts/commercial_assessment_instructions.md**
   - Complete documentation for agent behavior
   - Browser tool usage instructions
   - Example validations with expected outputs

### Code Changes

**tools.py - New web_search_brand() function:**
```python
def web_search_brand(brandname: str) -> Dict[str, Any]:
    """
    Search the web for brand information using AWS Bedrock AgentCore Browser.
    
    Returns instructions for the agent to perform web searches.
    The agent will use its browser tool to search and analyze results.
    """
    return {
        "action": "web_search_required",
        "brandname": brandname,
        "instructions": {
            "searches_to_perform": [
                f"{brandname} official website",
                f"{brandname} Wikipedia",
                f"{brandname} company information"
            ],
            "analysis_criteria": { ... },
            "confidence_scores": { ... }
        }
    }
```

**tools.py - Updated verify_brand_exists():**
```python
# After checking MCP and internal database...
# If brand not found, return web_search_required
web_search_instructions = web_search_brand(brandname)
return {
    "exists": None,  # Unknown - requires web search
    "confidence": 0.5,
    "source": "web_search_required",
    "web_search_instructions": web_search_instructions,
    "note": "Agent should use browser tool to search for this brand"
}
```

## Agent Instructions

The agent now has detailed instructions on how to use the Browser tool:

### When to Use Browser

When `verify_brand_exists_tool` returns:
```python
{
    "source": "web_search_required",
    "web_search_instructions": { ... }
}
```

### How to Use Browser

1. **Navigate to search engine**
   - Go to Google, Bing, or DuckDuckGo
   - Example: https://www.google.com

2. **Perform searches**
   - Enter search query from instructions
   - Submit search
   - Analyze first page of results

3. **Look for indicators**
   - Official company websites
   - Wikipedia pages
   - News articles
   - Business listings
   - Social media profiles

4. **Extract information**
   - Company name (official)
   - Business description
   - Industry/sector
   - Evidence of legitimacy

5. **Assign confidence score**
   - Based on findings
   - Use provided scoring guidelines

6. **Return result**
   - Include detailed reasoning
   - Specify what was found
   - Provide confidence score

## Example Validations

### Example 1: Brand in Registry

**Input:** "Starbucks", "Food & Beverage"

**Process:**
1. Check Brand Registry MCP → Found
2. Return immediately

**Output:**
```python
{
    "exists": True,
    "confidence": 0.95,
    "source": "brand_registry_mcp",
    "reasoning": "Brand found in Brand Registry MCP"
}
```

### Example 2: Brand Not in Registry (Browser Search Success)

**Input:** "Local Coffee Shop", "Food & Beverage"

**Process:**
1. Check Brand Registry MCP → Not found
2. Tool returns: web_search_required
3. Agent uses browser to search: "Local Coffee Shop official website"
4. Browser finds: Professional website at localcoffeeshop.com
5. Agent uses browser to search: "Local Coffee Shop Wikipedia"
6. Browser finds: No Wikipedia page
7. Agent analyzes: Legitimate local business

**Output:**
```python
{
    "exists": True,
    "confidence": 0.75,
    "source": "web_search",
    "official_name": "Local Coffee Shop",
    "reasoning": "Official website found at localcoffeeshop.com showing coffee shop business. No Wikipedia page but website confirms Food & Beverage sector. Website appears professional with menu, locations, and company information."
}
```

### Example 3: Brand Not Found (Browser Search Failure)

**Input:** "Fake Brand XYZ", "Retail"

**Process:**
1. Check Brand Registry MCP → Not found
2. Tool returns: web_search_required
3. Agent uses browser to search: "Fake Brand XYZ official website"
4. Browser finds: No credible results, only spam/parked domains
5. Agent uses browser to search: "Fake Brand XYZ company"
6. Browser finds: No credible business listings

**Output:**
```python
{
    "exists": False,
    "confidence": 0.20,
    "source": "web_search",
    "reasoning": "No credible online presence found. Browser searches for 'Fake Brand XYZ official website' and 'Fake Brand XYZ company' returned no legitimate results. No official website, Wikipedia page, or business listings found. Brand likely does not exist."
}
```

## Confidence Scoring

| Finding | Confidence | Use Case |
|---------|------------|----------|
| Brand Registry MCP | 0.95 | Brand in your database |
| Website + Wikipedia | 0.85 | Major brand with strong online presence |
| Website only | 0.75 | Legitimate business with web presence |
| Multiple mentions | 0.60 | Some online presence |
| Limited presence | 0.40 | Small/local business |
| No presence | 0.20 | Likely not legitimate |

## Advantages

✅ **Free** - No API costs, included with AgentCore
✅ **Comprehensive** - Can validate any brand with online presence
✅ **Secure** - Isolated browser environment
✅ **Observable** - Live view and session recording available
✅ **Managed** - No infrastructure to maintain
✅ **Integrated** - Works seamlessly with Strands Agents

## Deployment

### Prerequisites

1. **AWS Bedrock AgentCore** - Agents deployed to AgentCore runtime
2. **Strands Agents** - Using Strands framework (already in place)
3. **IAM Permissions** - Browser tool permissions for agents

### IAM Permissions Required

Add these permissions to your agent execution role:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:CreateBrowser",
                "bedrock-agentcore:StartBrowserSession",
                "bedrock-agentcore:StopBrowserSession",
                "bedrock-agentcore:ConnectBrowserAutomationStream"
            ],
            "Resource": "arn:aws:bedrock-agentcore:eu-west-1:*:browser/*"
        }
    ]
}
```

### Deployment Steps

1. **Update agent code**
   ```bash
   # Deploy updated Commercial Assessment Agent
   python infrastructure/deploy_agents.py --agent commercial_assessment
   ```

2. **Verify IAM permissions**
   - Check agent execution role has Browser permissions
   - Ensure region is eu-west-1

3. **Test with sample brands**
   - Test with known brands (should find in registry)
   - Test with unknown brands (should use browser)
   - Test with fake brands (should return low confidence)

4. **Monitor performance**
   - Check CloudWatch logs for browser usage
   - Monitor confidence scores
   - Review validation accuracy

## Monitoring

### What to Monitor

1. **Browser Usage**
   - How often is browser tool used?
   - Average search time
   - Success rate

2. **Validation Accuracy**
   - Are brands correctly identified?
   - Do confidence scores match reality?
   - Any false positives/negatives?

3. **Performance**
   - Browser search latency
   - Overall validation time
   - Impact on workflow

### CloudWatch Metrics

- Browser session count
- Browser session duration
- Validation success rate
- Confidence score distribution

### Live View

You can view browser sessions in real-time:
1. Navigate to AgentCore Browser Console
2. Select your browser tool
3. Find active session
4. Click "View live session"

## Testing

### Test Cases

| Brand | Expected Source | Expected Confidence | Expected Result |
|-------|----------------|---------------------|-----------------|
| Starbucks | brand_registry_mcp | 0.95 | Found in registry |
| McDonald's | brand_registry_mcp | 0.95 | Found in registry |
| Amazon | brand_registry_mcp or web_search | 0.85-0.95 | Major brand |
| Local Shop | web_search | 0.60-0.75 | Website found |
| Fake Brand | web_search | 0.20 | No presence |

### Testing Procedure

1. **Deploy updated agent**
2. **Test with known brands** (should find in registry)
3. **Test with brands not in registry** (should use browser)
4. **Test with fake brands** (should return low confidence)
5. **Review browser session logs**
6. **Verify confidence scores are appropriate**

## Alternative: Tavily API (Optional)

If browser tool proves too slow or complex, you can optionally add Tavily API:

### Tavily Pricing
- Free tier: 1,000 searches/month
- Paid: $1 per 1,000 searches

### Tavily Integration

1. **Install Tavily SDK**
   ```bash
   pip install tavily-python
   ```

2. **Add Tavily tool**
   ```python
   from tavily import TavilyClient
   
   @tool
   def tavily_search_tool(query: str) -> Dict[str, Any]:
       client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
       results = client.search(query=query, max_results=5)
       return results
   ```

3. **Update agent instructions**
   - Use Tavily instead of browser for web search
   - Simpler API, faster results
   - But costs money after free tier

## Troubleshooting

### Browser Sessions Not Starting

**Issue:** Agent can't start browser sessions

**Solution:**
- Check IAM permissions
- Verify region is eu-west-1
- Check CloudWatch logs for errors

### Slow Browser Searches

**Issue:** Browser searches take too long

**Solution:**
- Optimize search queries
- Reduce number of searches per brand
- Consider Tavily API as alternative

### Low Confidence Scores

**Issue:** All brands getting low confidence

**Solution:**
- Review agent instructions
- Check browser search results
- Verify analysis criteria

## Documentation

- **Agent Instructions:** `infrastructure/prompts/commercial_assessment_instructions.md`
- **Tool Implementation:** `agents/commercial_assessment/tools.py`
- **Agent Handler:** `agents/commercial_assessment/agentcore_handler.py`
- **AWS Browser Docs:** https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-tool.html

## Next Steps

1. **Deploy updated agent** to AWS Bedrock AgentCore
2. **Test with real brands** from your database
3. **Monitor browser usage** and performance
4. **Adjust confidence thresholds** if needed
5. **Consider Tavily** if browser proves insufficient

## Bottom Line

The Commercial Assessment Agent now uses **AWS Bedrock AgentCore Browser tool** for free, comprehensive brand validation. This is the correct solution for agents running in AgentCore runtime.

The agent will:
1. Check Brand Registry MCP first (fastest)
2. Use Browser tool for brands not in registry (free)
3. Analyze search results intelligently
4. Return appropriate confidence scores

This solution is implemented and ready to deploy!
