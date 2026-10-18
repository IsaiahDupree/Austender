# Implementation Guide: Enhancing Austender Scraping

This guide outlines the recommended implementation steps for building upon our multi-tool scraping approach, focusing on modular design, performance optimization, and robustness.

## Strategic Priorities

1. **Modular System Design** - Breaking down functionality into reusable components
2. **Fault Tolerance** - Implementing sophisticated error handling and recovery
3. **Performance Optimization** - Using asynchronous processing for intensive tasks
4. **Maintainability** - Ensuring code is well-documented and follows consistent patterns

## Implementation Roadmap

### Phase 1: Core Enhancements

#### 1.1 Modularize the Multi-Tool Scraper

Break down the monolithic `multi_tool_atm_scraper.py` into smaller, focused modules:

```
multi_tool/
├── __init__.py
├── core.py           # Core scraper class and main logic
├── browsers/
│   ├── __init__.py
│   ├── playwright.py # Playwright-specific implementation
│   ├── httpx.py      # Direct HTTP implementation
│   └── utils.py      # Shared browser utilities
├── extractors/
│   ├── __init__.py
│   ├── table.py      # Table data extraction
│   ├── detail.py     # Detailed page extraction
│   └── parser.py     # HTML parsing utilities
└── analysis/
    ├── __init__.py
    ├── ai.py         # AI-powered analysis
    ├── screenshots.py # Screenshot processing
    └── reporting.py  # Results reporting
```

**Implementation Example for the Modular Structure:**

```python
# multi_tool/core.py
from .browsers import playwright, httpx
from .extractors import table, detail
from .analysis import ai, screenshots

class MultiToolScraper:
    """Core scraper class orchestrating the different modules."""
    
    def __init__(self, config):
        self.config = config
        # Initialize components
        self.browsers = {
            "playwright": playwright.PlaywrightBrowser(config),
            "httpx": httpx.HttpxClient(config)
        }
        self.extractors = {
            "table": table.TableExtractor(),
            "detail": detail.DetailExtractor()
        }
        self.analyzers = {
            "ai": ai.AIAnalyzer(config),
            "screenshots": screenshots.ScreenshotAnalyzer()
        }
    
    async def execute(self):
        """Execute the scraping process with fallbacks."""
        # Implementation continues...
```

#### 1.2 Implement an Advanced Error Recovery System

Create a sophisticated error recovery system with categorized errors and specific recovery strategies:

```python
# multi_tool/recovery.py
class RecoveryStrategy:
    def __init__(self):
        self.strategies = {
            "timeout": [
                self.clear_cookies,
                self.reload_page,
                self.switch_browser
            ],
            "navigation": [
                self.restart_browser,
                self.try_alternative_route,
                self.delay_and_retry
            ],
            "selector": [
                self.try_alternative_selectors,
                self.analyze_structure,
                self.fallback_extraction
            ],
            "blocked": [
                self.switch_ip,
                self.switch_browser,
                self.wait_longer_retry
            ]
        }
    
    async def handle_error(self, error_type, context):
        """Apply appropriate recovery strategies for the error type."""
        for strategy in self.strategies.get(error_type, [self.generic_recovery]):
            if await strategy(context):
                return True
        return False
    
    # Specific recovery methods follow...
```

### Phase 2: Performance Optimization

#### 2.1 Implement Parallel Processing

Use asyncio to parallelize certain operations:

```python
async def extract_multiple_pages(self, urls):
    """Extract data from multiple detail pages in parallel."""
    tasks = []
    for url in urls:
        tasks.append(asyncio.create_task(self.extract_detail_page(url)))
    
    # Gather results with timeout protection
    results = []
    for task in asyncio.as_completed(tasks, timeout=60):
        try:
            result = await task
            if result:
                results.append(result)
        except asyncio.TimeoutError:
            logger.warning(f"Task timed out")
        except Exception as e:
            logger.error(f"Task error: {str(e)}")
    
    return results
```

#### 2.2 Implement Efficient Caching

Add a caching layer to minimize redundant requests:

```python
# multi_tool/cache.py
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

class Cache:
    def __init__(self, cache_dir="cache", ttl_hours=24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
    
    def _get_cache_key(self, url, params=None):
        """Generate a cache key from URL and optional params."""
        key = url
        if params:
            key += json.dumps(params, sort_keys=True)
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, url, params=None):
        """Get cached response if available and not expired."""
        key = self._get_cache_key(url, params)
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            
            # Check if cache is expired
            cached_time = datetime.fromisoformat(data["timestamp"])
            if datetime.now() - cached_time > self.ttl:
                return None
            
            return data["content"]
        except Exception:
            return None
    
    def set(self, url, content, params=None):
        """Cache response content."""
        key = self._get_cache_key(url, params)
        cache_file = self.cache_dir / f"{key}.json"
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "params": params,
            "content": content
        }
        
        with open(cache_file, "w") as f:
            json.dump(data, f)
```

### Phase 3: Advanced Anti-Detection

#### 3.1 Browser Fingerprint Randomization

Implement more sophisticated browser fingerprint randomization:

```python
async def randomize_fingerprint(self, page):
    """Apply random browser fingerprints to avoid detection."""
    # Choose random values for fingerprinting
    screen_width = random.choice([1366, 1440, 1536, 1920, 2560])
    screen_height = random.choice([768, 900, 864, 1080, 1440])
    is_mobile = random.random() > 0.9  # 10% chance of mobile
    
    # Apply fingerprint modifications
    await page.evaluate(f"""() => {{
        // Override properties that might be used for fingerprinting
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {random.randint(2, 16)}
        }});
        
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {random.choice([2, 4, 8, 16])}
        }});
        
        Object.defineProperty(navigator, 'platform', {{
            get: () => "{random.choice(['Win32', 'MacIntel', 'Linux x86_64'])}"
        }});
        
        Object.defineProperty(screen, 'width', {{
            get: () => {screen_width}
        }});
        
        Object.defineProperty(screen, 'height', {{
            get: () => {screen_height}
        }});
        
        // Many more fingerprint modifications...
    }}""")
```

#### 3.2 Dynamic Timing Patterns

Implement more realistic timing patterns:

```python
class HumanTimingSimulator:
    """Simulates human-like timing patterns for interactions."""
    
    def __init__(self):
        # Different timing profiles
        self.profiles = {
            "fast_reader": {
                "page_scan": (2.0, 5.0),
                "form_fill": (0.1, 0.3),
                "click_delay": (0.2, 0.5),
                "navigation_wait": (1.5, 3.0)
            },
            "average_user": {
                "page_scan": (4.0, 8.0),
                "form_fill": (0.2, 0.5),
                "click_delay": (0.3, 0.7),
                "navigation_wait": (2.0, 4.0)
            },
            "careful_reader": {
                "page_scan": (7.0, 15.0),
                "form_fill": (0.3, 0.7),
                "click_delay": (0.5, 1.0),
                "navigation_wait": (3.0, 5.0)
            }
        }
        # Randomly select a profile for this session
        self.current_profile = random.choice(list(self.profiles.keys()))
    
    async def wait_for_action(self, action_type):
        """Wait for a realistic amount of time based on action type."""
        profile = self.profiles[self.current_profile]
        min_time, max_time = profile.get(action_type, (0.5, 1.5))
        
        # Add some randomness to the timing pattern
        if random.random() > 0.8:  # 20% chance of distraction
            # Simulate user distraction
            wait_time = random.uniform(min_time * 2, max_time * 3)
        else:
            wait_time = random.uniform(min_time, max_time)
            
        await asyncio.sleep(wait_time)
```

### Phase 4: Testing and Monitoring

#### 4.1 Enhanced Test Harness

Extend the test harness to track more metrics:

```python
class EnhancedTestMetrics:
    """Collects and analyzes detailed test metrics."""
    
    def __init__(self):
        self.metrics = {}
    
    def start_test(self, test_id, approach):
        """Start tracking a test."""
        self.metrics[test_id] = {
            "approach": approach,
            "start_time": time.time(),
            "status": "running",
            "steps": [],
            "resources": {
                "memory_usage": [],
                "cpu_usage": []
            },
            "network": {
                "requests": 0,
                "data_transferred": 0,
                "response_times": []
            }
        }
    
    def record_step(self, test_id, step_name, success, duration, data=None):
        """Record a test step."""
        self.metrics[test_id]["steps"].append({
            "name": step_name,
            "success": success,
            "duration": duration,
            "timestamp": time.time(),
            "data": data
        })
    
    def record_resource_usage(self, test_id):
        """Record current resource usage."""
        import psutil
        process = psutil.Process()
        self.metrics[test_id]["resources"]["memory_usage"].append({
            "timestamp": time.time(),
            "value": process.memory_info().rss / 1024 / 1024  # MB
        })
        self.metrics[test_id]["resources"]["cpu_usage"].append({
            "timestamp": time.time(),
            "value": process.cpu_percent()
        })
    
    def end_test(self, test_id, success, data_count, error=None):
        """End a test and finalize metrics."""
        self.metrics[test_id]["end_time"] = time.time()
        self.metrics[test_id]["duration"] = (
            self.metrics[test_id]["end_time"] - self.metrics[test_id]["start_time"]
        )
        self.metrics[test_id]["status"] = "success" if success else "failed"
        self.metrics[test_id]["data_count"] = data_count
        if error:
            self.metrics[test_id]["error"] = str(error)
    
    def generate_report(self, output_path):
        """Generate detailed metrics report."""
        # Implementation for generating charts and statistics
```

#### 4.2 Site Structure Monitoring

Implement a system to detect site structure changes:

```python
class SiteStructureMonitor:
    """Monitors for changes in the Austender site structure."""
    
    def __init__(self, baseline_path="baselines"):
        self.baseline_path = Path(baseline_path)
        self.baseline_path.mkdir(exist_ok=True)
    
    async def capture_baseline(self, page, page_name):
        """Capture baseline for a specific page type."""
        structure = await self._extract_structure(page)
        
        baseline_file = self.baseline_path / f"{page_name}_structure.json"
        
        # Save current structure as baseline if none exists
        if not baseline_file.exists():
            with open(baseline_file, "w") as f:
                json.dump(structure, f, indent=2)
            return {"status": "baseline_created", "differences": None}
        
        # Compare with existing baseline
        with open(baseline_file, "r") as f:
            baseline = json.load(f)
        
        differences = self._compare_structures(baseline, structure)
        
        if differences["has_changes"]:
            # Save the new structure as a variant
            variant_file = self.baseline_path / f"{page_name}_variant_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(variant_file, "w") as f:
                json.dump({
                    "structure": structure,
                    "differences": differences
                }, f, indent=2)
        
        return {
            "status": "compared", 
            "has_changes": differences["has_changes"],
            "differences": differences
        }
    
    async def _extract_structure(self, page):
        """Extract structural information from the page."""
        return await page.evaluate("""() => {
            function extractStructure(element, maxDepth = 3, currentDepth = 0) {
                if (!element || currentDepth > maxDepth) return null;
                
                const result = {
                    tag: element.tagName?.toLowerCase(),
                    id: element.id || null,
                    classes: element.className?.split(' ').filter(c => c.trim().length > 0) || [],
                    attributes: {}
                };
                
                // Extract attributes
                for (const attr of element.attributes || []) {
                    if (attr.name !== 'id' && attr.name !== 'class') {
                        result.attributes[attr.name] = attr.value;
                    }
                }
                
                // For select important elements, get their children
                if (currentDepth < maxDepth) {
                    // Only include important elements at deeper levels
                    const children = Array.from(element.children).filter(child => {
                        const tag = child.tagName?.toLowerCase();
                        return ['table', 'form', 'div', 'nav', 'header', 'footer', 'main'].includes(tag) ||
                               child.id?.length > 0 ||
                               child.className?.length > 0;
                    });
                    
                    if (children.length > 0) {
                        result.children = children.map(child => 
                            extractStructure(child, maxDepth, currentDepth + 1)
                        ).filter(c => c !== null);
                    }
                }
                
                return result;
            }
            
            return extractStructure(document.body);
        }""")
    
    def _compare_structures(self, baseline, current):
        """Compare baseline and current structures to identify changes."""
        # Implementation of deep comparison logic
        # Returns detailed changes report
```

## Recommended Tech Stack Updates

Based on our testing, we recommend enhancing our stack with the following additional tools:

1. **playwright-stealth**: For enhanced anti-bot protection
   ```bash
   pip install playwright-stealth
   ```

2. **psutil**: For resource monitoring in testing
   ```bash
   pip install psutil
   ```

3. **aiohttp**: For additional HTTP client capabilities
   ```bash
   pip install aiohttp
   ```

4. **redis**: For distributed caching if needed
   ```bash
   pip install redis
   ```

## Best Practices for Ongoing Development

1. **Code Modularity**: Keep modules small and focused on a single responsibility

2. **Error Handling**: Implement comprehensive error handling with specific recovery strategies

3. **Testing First**: Add tests for new functionality before implementation

4. **Documentation**: Keep documentation up to date with code changes

5. **Monitoring**: Implement continuous monitoring for site changes

6. **Version Control**: Create feature branches for experiments and enhancements

7. **Performance Tracking**: Regularly benchmark performance metrics to identify regressions

## Deployment Considerations

1. **Resource Requirements**:
   - Memory: At least 2GB RAM for browser automation
   - CPU: 2+ cores recommended
   - Storage: 1GB+ for caching and storing results

2. **Scheduling**:
   - Avoid peak hours to minimize detection
   - Distribute crawling across different times
   - Implement exponential backoff for errors

3. **Scaling**:
   - Consider containerization with Docker
   - Use proxy rotation for high-volume scraping
   - Implement distributed scraping for very large datasets

This implementation guide provides a roadmap for enhancing our multi-tool scraper with a focus on modular design, performance optimization, and robust error handling. By following these guidelines, we can create a maintainable and effective system for Austender data extraction.
