#!/usr/bin/env python3
"""
Austender Scraping Test Harness
-------------------------------
This script systematically evaluates different scraping approaches for Austender
by running tests at scheduled intervals and comparing results.
"""

import os
import json
import time
import asyncio
import logging
import argparse
import datetime
import importlib
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Import scraper modules - use importlib for dynamic loading
import agentic_austender_browser
import focused_atm_scraper
import multi_tool_atm_scraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"test_harness_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.log")
    ]
)
logger = logging.getLogger("test_harness")

# Create output directories
os.makedirs("test_results", exist_ok=True)
os.makedirs("test_results/screenshots", exist_ok=True)
os.makedirs("test_reports", exist_ok=True)

class AustenderTestHarness:
    """Test harness for evaluating different Austender scraping approaches."""
    
    def __init__(self, 
                 keyword: str = "construction", 
                 state: str = None,
                 headless: bool = True,
                 debug: bool = False,
                 test_iterations: int = 3,
                 delay_between_tests: int = 300):
        """Initialize the test harness."""
        self.keyword = keyword
        self.state = state
        self.headless = headless
        self.debug = debug
        self.test_iterations = test_iterations
        self.delay_between_tests = delay_between_tests
        
        # Test configuration
        self.test_configs = [
            {
                "name": "agentic_browser",
                "description": "AI-driven browser agent approach",
                "module": "agentic_austender_browser",
                "class": "AgenticAustenderBrowser",
                "test_method": self.test_agentic_browser
            },
            {
                "name": "focused_scraper",
                "description": "Focused ATM scraper approach",
                "module": "focused_atm_scraper",
                "class": "FocusedATMScraper",
                "test_method": self.test_focused_scraper
            },
            {
                "name": "multi_tool_scraper",
                "description": "Multi-tool integration approach",
                "module": "multi_tool_atm_scraper",
                "class": "MultiToolATMScraper",
                "test_method": self.test_multi_tool
            }
        ]
        
        # Results tracking
        self.results = defaultdict(list)
        self.summary = {}
        
        logger.info(f"Test harness initialized with {len(self.test_configs)} test configurations")
    
    async def run_tests(self):
        """Run all configured tests with the specified iterations."""
        start_time = datetime.datetime.now()
        logger.info(f"Starting test run at {start_time}")
        
        overall_results = []
        
        # Run the specified number of iterations for each test
        for iteration in range(1, self.test_iterations + 1):
            iteration_start = datetime.datetime.now()
            logger.info(f"Starting test iteration {iteration}/{self.test_iterations}")
            
            iteration_results = {
                "iteration": iteration,
                "timestamp": iteration_start.isoformat(),
                "results": []
            }
            
            # Run each test configuration
            for config in self.test_configs:
                logger.info(f"Testing {config['name']} ({config['description']})")
                
                try:
                    # Run the appropriate test method
                    result = await config["test_method"]()
                    
                    # Store the result
                    self.results[config["name"]].append(result)
                    iteration_results["results"].append({
                        "test_name": config["name"],
                        "success": result["success"],
                        "data_count": len(result.get("data", [])),
                        "duration_seconds": result.get("duration_seconds", 0),
                        "error": result.get("error", None)
                    })
                    
                    logger.info(f"Test {config['name']} completed: success={result['success']}, " +
                               f"data_count={len(result.get('data', []))}, " +
                               f"duration={result.get('duration_seconds', 0):.2f}s")
                    
                except Exception as e:
                    logger.error(f"Error running test {config['name']}: {str(e)}")
                    self.results[config["name"]].append({
                        "success": False,
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                        "timestamp": datetime.datetime.now().isoformat()
                    })
                    iteration_results["results"].append({
                        "test_name": config["name"],
                        "success": False,
                        "data_count": 0,
                        "duration_seconds": 0,
                        "error": str(e)
                    })
            
            # Record the iteration results
            overall_results.append(iteration_results)
            
            # Wait between iterations (except for the last one)
            if iteration < self.test_iterations:
                delay_time = self.delay_between_tests
                logger.info(f"Waiting {delay_time} seconds before next iteration...")
                await asyncio.sleep(delay_time)
        
        # Generate summary after all tests complete
        end_time = datetime.datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        self.summary = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_duration_seconds": total_duration,
            "iterations_completed": self.test_iterations,
            "test_configurations": len(self.test_configs),
            "results_by_approach": {}
        }
        
        # Calculate success rates and statistics for each approach
        for config in self.test_configs:
            name = config["name"]
            test_results = self.results[name]
            
            success_count = sum(1 for r in test_results if r.get("success", False))
            data_counts = [len(r.get("data", [])) for r in test_results]
            avg_data_count = sum(data_counts) / len(data_counts) if data_counts else 0
            
            self.summary["results_by_approach"][name] = {
                "success_rate": success_count / len(test_results) if test_results else 0,
                "average_data_count": avg_data_count,
                "total_data_extracted": sum(data_counts),
                "error_rate": 1 - (success_count / len(test_results) if test_results else 0)
            }
        
        # Save results and summary
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"test_reports/test_summary_{timestamp}.json", "w") as f:
            json.dump({
                "summary": self.summary,
                "iterations": overall_results
            }, f, indent=2)
        
        logger.info(f"Testing completed. Summary saved to test_reports/test_summary_{timestamp}.json")
        return self.summary
    
    def generate_report(self):
        """Generate a human-readable report from the test results."""
        if not self.summary:
            logger.warning("No test results available for report generation")
            return
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"test_reports/report_{timestamp}.md"
        
        with open(report_path, "w") as f:
            f.write("# Austender Scraping Approaches Test Report\n\n")
            f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Test Configuration\n\n")
            f.write(f"- Keyword: {self.keyword}\n")
            f.write(f"- State: {self.state if self.state else 'All states'}\n")
            f.write(f"- Test iterations: {self.test_iterations}\n")
            f.write(f"- Headless mode: {self.headless}\n")
            f.write(f"- Debug mode: {self.debug}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- Test period: {self.summary['start_time']} to {self.summary['end_time']}\n")
            f.write(f"- Total duration: {self.summary['total_duration_seconds']:.2f} seconds\n")
            f.write(f"- Iterations completed: {self.summary['iterations_completed']}\n\n")
            
            f.write("## Results by Approach\n\n")
            f.write("| Approach | Success Rate | Avg. Data Count | Total Data | Error Rate |\n")
            f.write("|----------|--------------|-----------------|------------|------------|\n")
            
            for name, stats in self.summary["results_by_approach"].items():
                f.write(f"| {name} | {stats['success_rate']:.2%} | {stats['average_data_count']:.1f} | {stats['total_data_extracted']} | {stats['error_rate']:.2%} |\n")
            
            f.write("\n## Detailed Results\n\n")
            
            for config in self.test_configs:
                name = config["name"]
                f.write(f"### {name} ({config['description']})\n\n")
                
                for i, result in enumerate(self.results[name]):
                    f.write(f"#### Iteration {i+1}\n\n")
                    f.write(f"- Success: {result.get('success', False)}\n")
                    f.write(f"- Data extracted: {len(result.get('data', []))}\n")
                    f.write(f"- Duration: {result.get('duration_seconds', 0):.2f} seconds\n")
                    
                    if "error" in result and result["error"]:
                        f.write(f"- Error: {result['error']}\n")
                    
                    f.write("\n")
            
            f.write("## Recommendations\n\n")
            
            # Find the best performing approach
            success_rates = {name: stats["success_rate"] for name, stats in self.summary["results_by_approach"].items()}
            data_counts = {name: stats["average_data_count"] for name, stats in self.summary["results_by_approach"].items()}
            
            best_success = max(success_rates.items(), key=lambda x: x[1]) if success_rates else (None, 0)
            best_data = max(data_counts.items(), key=lambda x: x[1]) if data_counts else (None, 0)
            
            f.write(f"- Best success rate: **{best_success[0]}** ({best_success[1]:.2%})\n")
            f.write(f"- Best data extraction: **{best_data[0]}** (avg. {best_data[1]:.1f} items)\n\n")
            
            # Overall recommendation
            if best_success[0] == best_data[0]:
                f.write(f"**Overall recommendation:** The **{best_success[0]}** approach performed best in both success rate and data extraction.\n\n")
            else:
                f.write(f"**Overall recommendation:** Consider using **{best_success[0]}** for reliability and **{best_data[0]}** for maximum data extraction.\n\n")
        
        logger.info(f"Report generated: {report_path}")
        return report_path
        
    async def test_agentic_browser(self):
        """Test the AgenticAustenderBrowser approach."""
        start_time = time.time()
        result = {
            "timestamp": datetime.datetime.now().isoformat(),
            "success": False,
            "data": [],
            "approach": "agentic_browser"
        }
        
        try:
            # Initialize the browser
            browser = agentic_austender_browser.AgenticAustenderBrowser(
                headless=self.headless
            )
            
            # Start the browser
            await browser.start_browser()
            
            try:
                # Perform ATM search
                opportunities = await browser.search_opportunities(
                    keyword=self.keyword,
                    max_results=20
                )
                
                # Record results
                result["success"] = True
                result["data"] = opportunities
                
            finally:
                # Always close the browser
                await browser.close()
            
        except Exception as e:
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()
            logger.error(f"Error in agentic browser test: {str(e)}")
        
        # Calculate duration
        end_time = time.time()
        result["duration_seconds"] = end_time - start_time
        
        return result
    
    async def test_focused_scraper(self):
        """Test the FocusedATMScraper approach."""
        start_time = time.time()
        result = {
            "timestamp": datetime.datetime.now().isoformat(),
            "success": False,
            "data": [],
            "approach": "focused_scraper"
        }
        
        try:
            # Initialize the scraper
            scraper = focused_atm_scraper.FocusedATMScraper(
                headless=self.headless,
                debug=self.debug
            )
            
            try:
                # Start browser
                await scraper.start_browser()
                
                # Navigate to ATM search page
                success = await scraper.execute_with_retries(scraper.navigate_to_atm_search)
                if not success:
                    raise Exception("Failed to navigate to ATM search page")
                
                # Perform search
                search_success = await scraper.execute_with_retries(
                    scraper.search_atm, 
                    keyword=self.keyword, 
                    state=self.state
                )
                if not search_success:
                    raise Exception("Failed to perform ATM search")
                
                # Extract listings
                listings = await scraper.execute_with_retries(scraper.extract_atm_listings)
                
                # Record results
                result["success"] = len(listings) > 0
                result["data"] = listings
                
            finally:
                # Always close the browser
                await scraper.close()
            
        except Exception as e:
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()
            logger.error(f"Error in focused scraper test: {str(e)}")
        
        # Calculate duration
        end_time = time.time()
        result["duration_seconds"] = end_time - start_time
        
        return result
    
    async def test_multi_tool(self):
        """Test the MultiToolATMScraper approach."""
        start_time = time.time()
        result = {
            "timestamp": datetime.datetime.now().isoformat(),
            "success": False,
            "data": [],
            "approach": "multi_tool"
        }
        
        try:
            # Initialize the scraper
            scraper = multi_tool_atm_scraper.MultiToolATMScraper(
                headless=self.headless,
                debug=self.debug
            )
            
            # Set search parameters
            scraper.keyword = self.keyword
            if self.state:
                scraper.state = self.state
            
            # Execute with fallbacks
            scraper_result = await scraper.execute_with_fallbacks()
            
            # Record results
            result["success"] = scraper_result.get("success", False)
            result["data"] = scraper_result.get("data", [])
            result["method_used"] = scraper_result.get("method", "unknown")
            
        except Exception as e:
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()
            logger.error(f"Error in multi-tool test: {str(e)}")
        
        # Calculate duration
        end_time = time.time()
        result["duration_seconds"] = end_time - start_time
        
        return result

async def main():
    """Main function to run the test harness."""
    parser = argparse.ArgumentParser(description="Austender Scraping Test Harness")
    parser.add_argument("--keyword", type=str, default="construction",
                        help="Keyword to search (default: construction)")
    parser.add_argument("--state", type=str,
                        help="State to filter by (e.g., NSW)")
    parser.add_argument("--iterations", type=int, default=3,
                        help="Number of test iterations to run (default: 3)")
    parser.add_argument("--delay", type=int, default=300,
                        help="Delay between test iterations in seconds (default: 300)")
    parser.add_argument("--headless", action="store_true",
                        help="Run in headless mode")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode")
    parser.add_argument("--scheduled", action="store_true",
                        help="Run in scheduled mode at specific times")
    parser.add_argument("--schedule-times", type=str, default="09:00,13:00,17:00,21:00",
                        help="Comma-separated times to run in scheduled mode (default: 09:00,13:00,17:00,21:00)")
    
    args = parser.parse_args()
    
    if args.scheduled:
        # Run tests at specified times
        schedule_times = [t.strip() for t in args.schedule_times.split(",")]
        logger.info(f"Running in scheduled mode at times: {schedule_times}")
        
        while True:
            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M")
            
            if current_time in schedule_times:
                logger.info(f"Running scheduled test at {current_time}")
                
                # Initialize the test harness
                harness = AustenderTestHarness(
                    keyword=args.keyword,
                    state=args.state,
                    headless=args.headless,
                    debug=args.debug,
                    test_iterations=args.iterations,
                    delay_between_tests=args.delay
                )
                
                # Run tests
                await harness.run_tests()
                
                # Generate report
                harness.generate_report()
                
                # Wait until the next minute to avoid running multiple times
                await asyncio.sleep(60)
            else:
                # Wait for a minute before checking again
                await asyncio.sleep(60)
    else:
        # Run tests immediately
        logger.info("Running tests immediately")
        
        # Initialize the test harness
        harness = AustenderTestHarness(
            keyword=args.keyword,
            state=args.state,
            headless=args.headless,
            debug=args.debug,
            test_iterations=args.iterations,
            delay_between_tests=args.delay
        )
        
        # Run tests
        summary = await harness.run_tests()
        
        # Generate report
        report_path = harness.generate_report()
        
        # Print summary to console
        print("\n" + "="*50)
        print("TEST RESULTS SUMMARY")
        print("="*50)
        for approach, stats in summary["results_by_approach"].items():
            print(f"{approach}:")
            print(f"  Success Rate: {stats['success_rate']:.2%}")
            print(f"  Avg. Data Items: {stats['average_data_count']:.1f}")
            print(f"  Total Data Extracted: {stats['total_data_extracted']}")
            print(f"  Error Rate: {stats['error_rate']:.2%}")
        print("="*50)
        print(f"Detailed report saved to: {report_path}")
        print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
