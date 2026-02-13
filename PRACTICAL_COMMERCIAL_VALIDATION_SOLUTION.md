# Practical Solution: Commercial Brand Validation

## The Problem

Your Brand Registry MCP contains brand names and sectors from transaction data, but **NOT commercial validation information**. The Commercial Assessment Agent needs to verify if brands are real commercial entities.

## The Reality of "Free" APIs

After extensive research, here's the truth:

| Service | Cost | Reality |
|---------|------|---------|
| OpenCorporates | £2,250/year ($2,800/year) | NOT free (offers free for public benefit projects only) |
| Crunchbase | $299+/month | NOT free |
| Brave Search | $5/1000 requests | NOT free |
| Wikipedia MCP | N/A | Package doesn't exist in registries |
| Companies House (UK) | FREE | UK companies only, limited scope |
| SEC EDGAR (US) | FREE | US public companies only |

**Bottom line:** There are NO truly free, comprehensive commercial validation APIs with reasonable limits for retail brands.

## Recommended Solution: Use Kiro's Built-in Web Search

Kiro IDE has built-in web search capabilities that the Commercial Assessment Agent can use. This is the most practical solution.

### How It Works

1. **Agent-Level Web Search**
   - The Commercial Assessment Agent runs in Kiro IDE
   - Kiro agents have access to web search tools
   - The agent can search for brand information directly
   - No external API keys or costs required

2. **Search Strategy**
   - Search for: `"{brand_name}" company official website`
   - Search for: `"{brand_name}" Wikipedia`
   - Search for: `"{brand_name}" about company`
   - Analyze search results to determine if brand is legitimate

3. **Validation Criteria**
   - Official website exists
   - Wikipedia page exists
   - News articles mention the company
   - Social media presence
   - Business directory listings

### Implementation

The Commercial Assessment Agent's instructions should include:

```
When validating a brand:

1. Check the Brand Registry MCP first (your internal database)
2. If not found or needs external validation:
   - Use web search to find the brand's official website
   - Search for Wikipedia page
   - Look for news articles or business listings
3. Assess legitimacy based on:
   - Official website quality and content
   - Online presence and mentions
   - Consistency of information across sources
4. Return validation result with confidence score
```

### Advantages

✅ **Free** - Uses Kiro's built-in capabilities
✅ **No API keys** - No external dependencies
✅ **Comprehensive** - Can find any brand with online presence
✅ **Flexible** - Agent can adapt search strategy
✅ **Already available** - No setup required

### Limitations

⚠️ **Rate limits** - Kiro's web search may have rate limits
⚠️ **Slower** - Web search is slower than dedicated APIs
⚠️ **Less structured** - Results need interpretation
⚠️ **Requires agent intelligence** - Agent must analyze results

## Alternative: Hybrid Approach

Combine multiple free sources:

### 1. Brand Registry MCP (Your Data)
- **Cost:** FREE
- **Coverage:** Your 3,000+ brands
- **Use for:** Initial lookup

### 2. Kiro Web Search
- **Cost:** FREE (built-in)
- **Coverage:** Any brand with online presence
- **Use for:** External validation

### 3. Internal Known Brands List
- **Cost:** FREE
- **Coverage:** ~10 major brands (hardcoded)
- **Use for:** Fallback for common brands

### 4. Companies House API (UK Only)
- **Cost:** FREE
- **Coverage:** UK registered companies
- **API:** https://developer-specs.company-information.service.gov.uk/
- **Use for:** UK brands only

### 5. SEC EDGAR (US Only)
- **Cost:** FREE
- **Coverage:** US public companies
- **API:** https://www.sec.gov/edgar/sec-api-documentation
- **Use for:** Large US brands only

## Recommended Implementation

### Phase 1: Use What You Have (Now)

```python
def verify_brand_exists(brandname: str) -> Dict[str, Any]:
    # 1. Check Brand Registry MCP (your data)
    # 2. Check internal known brands list
    # 3. Return result with note to use web search
    
    return {
        "exists": None,  # Unknown
        "confidence": 0.5,
        "note": "Use web search in Kiro to validate this brand"
    }
```

### Phase 2: Agent Instructions (Immediate)

Update the Commercial Assessment Agent's instructions to use web search:

```
You are the Commercial Assessment Agent. Your role is to validate brand names.

When validating a brand:
1. Check if it exists in the Brand Registry MCP
2. If not found, use web search to validate:
   - Search: "{brand_name} official website"
   - Search: "{brand_name} Wikipedia"
   - Analyze results to determine legitimacy
3. Return validation with confidence score

Confidence scoring:
- 0.95: Found in Brand Registry MCP
- 0.85: Official website + Wikipedia page
- 0.75: Official website only
- 0.60: Multiple online mentions
- 0.40: Limited online presence
- 0.20: No credible online presence
```

### Phase 3: Optional Paid Services (If Budget Allows)

If you get budget approval:
- **OpenCorporates:** £2,250/year for 500 API calls/month
- **Brave Search:** $5/1000 requests
- **Crunchbase:** $299+/month

## Immediate Action Items

1. **Update Commercial Assessment Agent instructions** to use web search
2. **Test with a few brands** to see if web search provides adequate validation
3. **Monitor performance** - if web search is too slow or unreliable, consider paid options
4. **Document the process** for your team

## Testing the Solution

Try validating these brands using web search in Kiro:

1. **Starbucks** - Should find official website, Wikipedia, high confidence
2. **McDonald's** - Should find official website, Wikipedia, high confidence
3. **Local Coffee Shop** - May find website, lower confidence
4. **Fake Brand XYZ** - Should find nothing, very low confidence

## Bottom Line

**Use Kiro's built-in web search for commercial validation.** It's free, available now, and can validate any brand with an online presence. This is the most practical solution given the lack of truly free commercial validation APIs.

If web search proves insufficient, you can evaluate paid options later with actual usage data to justify the cost.
