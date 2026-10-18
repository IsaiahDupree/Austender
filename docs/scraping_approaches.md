# Austender Scraping Technical Documentation

## Overview

This document details the various technical approaches implemented for scraping the Australian Tender Market (ATM) listings from the Austender website. Due to the complexity of the site and its anti-bot measures, we've developed multiple scraping strategies with different strengths and fallback mechanisms.

## Table of Contents

1. [Scraping Challenges](#scraping-challenges)
2. [Implemented Approaches](#implemented-approaches)
   - [Agentic Browser Approach](#agentic-browser-approach)
   - [Focused ATM Scraper](#focused-atm-scraper)
   - [Multi-Tool Integration](#multi-tool-integration)
3. [Technical Implementation Details](#technical-implementation-details)
   - [Anti-Bot Measures](#anti-bot-measures)
   - [Selectors Strategy](#selectors-strategy)
   - [Data Extraction Patterns](#data-extraction-patterns)
4. [Testing and Evaluation](#testing-and-evaluation)
5. [Recommendations](#recommendations)

## Scraping Challenges

The Austender website presents several challenges for automated data extraction:

1. **Anti-Bot Protection**: The site employs measures to detect and block automated scraping
2. **Dynamic Content**: Many elements load dynamically via JavaScript
3. **Session Management**: Session tracking and possible IP-based rate limiting
4. **Structural Complexity**: Complex DOM structure with inconsistent patterns
5. **Regular Changes**: Periodic updates to the site structure requiring adaptation

## Implemented Approaches

We've developed three primary scraping approaches, each with different strengths:

### Agentic Browser Approach

**File**: `agentic_austender_browser.py`

This approach uses an AI-driven browser agent with OpenAI for decision-making and Playwright for browser automation.

**Key Features**:
- General-purpose browser automation for the entire Austender site
- AI-powered decision making for navigation and extraction
- Basic anti-detection measures
- Best for exploratory tasks and adapting to site changes

**Limitations**:
- Higher resource usage due to AI integration
- Less focused on ATM-specific patterns
- More complex execution flow

**Usage Example**:
```python
from agentic_austender_browser import AgenticAustenderBrowser

async def main():
    browser = AgenticAustenderBrowser(headless=False)
    await browser.start_browser()
    
    try:
        opportunities = await browser.search_opportunities(
            keyword="construction", 
            max_results=20
        )
        print(f"Found {len(opportunities)} opportunities")
    finally:
        await browser.close()
```

### Focused ATM Scraper

**File**: `focused_atm_scraper.py`

This approach specifically targets ATM listings with enhanced selectors and multiple extraction strategies.

**Key Features**:
- Multiple specific selectors targeting ATM table structures
- Screenshot analysis with OpenAI for debugging
- Enhanced error handling and recovery
- Multiple fallback extraction methods
- More efficient for targeted ATM extraction

**Key Selectors**:
- `table.searchResults tr[class^='row']`
- `.results-table tbody tr`
- `table#ATMSearchResults tr`
- `table tr.atm-result-row`
- `table tbody tr[data-atmid]`
- `table tr:has(td a[href*='ATM/View'])`

**Usage Example**:
```python
from focused_atm_scraper import FocusedATMScraper

async def main():
    scraper = FocusedATMScraper(headless=False, debug=True)
    
    try:
        await scraper.start_browser()
        await scraper.navigate_to_atm_search()
        await scraper.search_atm(keyword="bridge construction", state="NSW")
        listings = await scraper.extract_atm_listings()
        print(f"Extracted {len(listings)} ATM listings")
    finally:
        await scraper.close()
```

### Multi-Tool Integration

**File**: `multi_tool_atm_scraper.py`

Our most comprehensive approach integrating multiple tools with sophisticated fallback strategies.

**Key Features**:
- Multiple fallback strategies:
  - Primary: Playwright with stealth mode
  - Secondary: Direct HTTP requests with headers rotation
  - Tertiary: Alternative browser engines
- AI-powered screenshot analysis for debugging
- Proxy support for IP rotation
- Enhanced human-like behavior simulation
- Most resilient against anti-bot measures

**Usage Example**:
```python
from multi_tool_atm_scraper import MultiToolATMScraper

async def main():
    scraper = MultiToolATMScraper(headless=False, debug=True)
    scraper.keyword = "bridge construction"
    scraper.state = "NSW"
    
    results = await scraper.execute_with_fallbacks()
    
    if results["success"]:
        print(f"Successfully extracted {len(results['data'])} ATM listings using {results['method']}")
    else:
        print("Extraction failed with all methods")
```

## Technical Implementation Details

### Anti-Bot Measures

We've implemented several techniques to avoid detection as a bot:

1. **Browser Fingerprint Modification**:
   ```javascript
   Object.defineProperty(navigator, 'webdriver', { get: () => false });
   ```

2. **User-Agent Rotation**:
   ```python
   user_agent = random.choice(USER_AGENTS)
   ```

3. **Human-like Behavior Simulation**:
   ```python
   async def simulate_human_behavior(self):
       # Random mouse movements
       for _ in range(random.randint(3, 6)):
           x = random.randint(100, dimensions["width"] - 200)
           y = random.randint(100, dimensions["height"] - 200)
           await self.page.mouse.move(x, y)
           await asyncio.sleep(random.uniform(0.1, 0.3))
       
       # Random scrolling
       await self.page.evaluate(f"window.scrollBy(0, {random.randint(300, 800)})")
   ```

4. **Multi-Stage Navigation**:
   ```python
   # Instead of directly visiting the target URL:
   await self.page.goto(BASE_URL)  # Visit main site first
   await self.simulate_human_behavior()
   
   # Then find and click the appropriate link
   for selector in selectors:
       element = await self.page.query_selector(selector)
       if element:
           await element.click()
           break
   ```

5. **Browser Rotation** when encounters issues:
   ```python
   browser_types = ["chromium", "firefox", "webkit"]
   current_browser_index = (current_browser_index + 1) % len(browser_types)
   await self.start_browser(browser_type=browser_types[current_browser_index])
   ```

### Selectors Strategy

Our selector strategy follows a fallback pattern, trying multiple selectors for each element:

```python
selectors = [
    "table.searchResults tr[class^='row']",  # Most specific
    ".results-table tbody tr",               # Common pattern
    "table#ATMSearchResults tr",             # ID-based
    "table tr.atm-result-row",               # Class-based
    "table tbody tr[data-atmid]",            # Data attribute
    "table tr:has(td a[href*='ATM/View'])"   # Functional
]

for selector in selectors:
    rows = await self.page.query_selector_all(selector)
    if len(rows) > 0:
        # Process using this selector
        break
```

### Data Extraction Patterns

We extract data using multiple patterns:

1. **Attribute-based extraction**:
   ```python
   atm_id = await row.get_attribute("data-atmid") or ""
   agency = await row.get_attribute("data-agency") or ""
   ```

2. **Cell-based extraction**:
   ```python
   cells = await row.query_selector_all("td")
   atm_id = await cells[0].text_content() if len(cells) > 0 else ""
   agency = await cells[1].text_content() if len(cells) > 1 else ""
   ```

3. **Link extraction**:
   ```python
   link = await row.query_selector("a[href*='ATM/View']")
   url = await link.get_attribute("href") if link else ""
   ```

## Testing and Evaluation

We've developed a comprehensive test harness (`austender_test_harness.py`) to systematically evaluate the performance of each approach:

- Runs multiple iterations of each scraping approach
- Tracks success rates, data extracted, and performance metrics
- Generates comparative reports
- Supports scheduled runs to identify time-based patterns

Example test command:
```bash
python austender_test_harness.py --keyword "bridge construction" --state "NSW" --iterations 3
```

## Recommendations

Based on our development and testing:

1. **Use Multi-Tool Approach for Production**: The `multi_tool_atm_scraper.py` provides the most reliable results with its multiple fallback strategies

2. **Schedule Scraping at Different Times**: The site may have varying levels of protection at different times

3. **Regularly Monitor for Changes**: Use the AI-powered screenshot analysis to detect and adapt to site changes

4. **Consider Proxy Rotation**: For large-scale scraping, implement rotating proxies to avoid IP-based blocking

5. **Update Selectors Frequently**: Maintain a library of working selectors and update them as the site evolves
