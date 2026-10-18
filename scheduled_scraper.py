#!/usr/bin/env python3
"""
Scheduled Multi-Tool Austender Scraper
--------------------------------------
Runs the scraper at scheduled times with enhanced tool integration
and comprehensive logging for pattern analysis.
"""

import os
import json
import time
import random
import asyncio
import logging
import argparse
import schedule
from datetime import datetime, timedelta
from pathlib import Path

# Import our multi-tool scraper
from multi_tool_atm_scraper import MultiToolATMScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"scheduled_scraper_{datetime.now().strftime('%Y%m%d_%H%M')}.log")
    ]
)
logger = logging.getLogger("scheduled_scraper")

# Create directories
os.makedirs("scheduled_runs", exist_ok=True)
os.makedirs("scheduled_runs/data", exist_ok=True)
os.makedirs("scheduled_runs/logs", exist_ok=True)
os.makedirs("scheduled_runs/screenshots", exist_ok=True)

class ScheduledScraper:
    """Runs the scraper at scheduled times with enhanced integration."""
    
    def __init__(self, config=None):
        """Initialize the scheduled scraper with configuration."""
        self.config = config or {}
        self.runs_log = Path("scheduled_runs/runs_log.json")
        
        # Load run history if exists
        if self.runs_log.exists():
            with open(self.runs_log, "r") as f:
                self.runs = json.load(f)
        else:
            self.runs = []
        
        # Default schedule if none provided
        self.schedule_times = self.config.get("schedule_times", [
            "06:00", "09:00", "12:00", "15:00", "18:00", "21:00", "00:00", "03:00"
        ])
        
        # Search parameters
        self.keywords = self.config.get("keywords", ["construction", "infrastructure", "bridge"])
        self.states = self.config.get("states", ["NSW", "VIC", "QLD", "ACT", "SA", "WA", "NT", "TAS"])
        
        # Tool integration flags
        self.use_firecrawl = self.config.get("use_firecrawl", True)
        self.use_proxy = self.config.get("use_proxy", False)
        self.use_browser_rotation = self.config.get("use_browser_rotation", True)
        
        # Success/failure trackers
        self.success_patterns = {}
        self.failure_patterns = {}
        
        logger.info(f"Initialized scheduled scraper with {len(self.schedule_times)} schedule times")
    
    def setup_schedule(self):
        """Set up the schedule for running scraper jobs."""
        logger.info(f"Setting up schedule for times: {', '.join(self.schedule_times)}")
        
        for time_str in self.schedule_times:
            schedule.every().day.at(time_str).do(self.run_scraper_job)
            logger.info(f"Scheduled job for {time_str}")
        
        # Also add a random time slot for unpredictability
        random_hour = random.randint(8, 17)
        random_minute = random.randint(0, 59)
        random_time = f"{random_hour:02d}:{random_minute:02d}"
        schedule.every().day.at(random_time).do(self.run_scraper_job)
        logger.info(f"Added random schedule at {random_time}")
    
    async def run_scraper_with_tool(self, keyword, state=None):
        """Run the appropriate scraper tool based on configuration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"run_{timestamp}_{keyword}_{state or 'all'}"
        run_data = {
            "id": run_id,
            "timestamp": datetime.now().isoformat(),
            "keyword": keyword,
            "state": state,
            "success": False,
            "data_count": 0,
            "tool_used": None,
            "duration_seconds": 0
        }
        
        logger.info(f"Starting scraper run {run_id}")
        start_time = time.time()
        
        try:
            # Initialize the Multi-Tool scraper
            scraper = MultiToolATMScraper(
                headless=True,  # Run headless for scheduled jobs
                debug=True,     # Enable debug for better logging
                browser_type=random.choice(["chromium", "firefox", "webkit"]) if self.use_browser_rotation else "chromium",
                use_proxy=self.use_proxy
            )
            
            # Set search parameters
            scraper.keyword = keyword
            if state:
                scraper.state = state
            
            # Execute with fallbacks
            results = await scraper.execute_with_fallbacks()
            
            # Check if we got data
            if results["success"] and results["data"]:
                run_data["success"] = True
                run_data["data_count"] = len(results["data"])
                run_data["tool_used"] = results.get("method", "unknown")
                
                # Save the extracted data
                data_file = f"scheduled_runs/data/{run_id}.json"
                with open(data_file, "w") as f:
                    json.dump(results["data"], f, indent=2)
                logger.info(f"Saved {len(results['data'])} items to {data_file}")
                
                # Update success patterns
                time_of_day = datetime.now().hour
                day_of_week = datetime.now().weekday()
                pattern_key = f"{day_of_week}_{time_of_day}"
                
                if pattern_key not in self.success_patterns:
                    self.success_patterns[pattern_key] = 0
                self.success_patterns[pattern_key] += 1
            else:
                # Update failure patterns
                time_of_day = datetime.now().hour
                day_of_week = datetime.now().weekday()
                pattern_key = f"{day_of_week}_{time_of_day}"
                
                if pattern_key not in self.failure_patterns:
                    self.failure_patterns[pattern_key] = 0
                self.failure_patterns[pattern_key] += 1
                
                logger.warning(f"No data extracted in run {run_id}")
        
        except Exception as e:
            run_data["error"] = str(e)
            logger.error(f"Error in scraper run {run_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        finally:
            # Calculate duration
            end_time = time.time()
            duration = end_time - start_time
            run_data["duration_seconds"] = duration
            
            # Add to runs history
            self.runs.append(run_data)
            with open(self.runs_log, "w") as f:
                json.dump(self.runs, f, indent=2)
            
            logger.info(f"Completed run {run_id} in {duration:.2f} seconds, success: {run_data['success']}")
            
            # Save pattern analysis periodically
            if len(self.runs) % 5 == 0:
                self.save_pattern_analysis()
            
            return run_data
    
    def run_scraper_job(self):
        """Run a scraper job with random keyword and state."""
        # Select a random keyword and state for variety
        keyword = random.choice(self.keywords)
        state = random.choice(self.states + [None])  # Sometimes try without state filter
        
        logger.info(f"Running scheduled job with keyword: {keyword}, state: {state or 'all'}")
        
        # Use asyncio to run the async scraper
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.run_scraper_with_tool(keyword, state))
            return result
        finally:
            loop.close()
    
    def save_pattern_analysis(self):
        """Save analysis of success/failure patterns."""
        analysis = {
            "success_patterns": self.success_patterns,
            "failure_patterns": self.failure_patterns,
            "total_runs": len(self.runs),
            "successful_runs": sum(1 for run in self.runs if run.get("success", False)),
            "total_items_extracted": sum(run.get("data_count", 0) for run in self.runs),
            "average_duration": sum(run.get("duration_seconds", 0) for run in self.runs) / len(self.runs) if self.runs else 0,
            "tools_used": {}
        }
        
        # Count usage of different tools
        for run in self.runs:
            tool = run.get("tool_used")
            if tool:
                if tool not in analysis["tools_used"]:
                    analysis["tools_used"][tool] = 0
                analysis["tools_used"][tool] += 1
        
        # Find best times
        best_times = []
        for pattern, count in self.success_patterns.items():
            day, hour = pattern.split("_")
            best_times.append({
                "day": int(day),  # 0=Monday, 6=Sunday
                "hour": int(hour),
                "success_count": count,
                "success_rate": count / (count + self.failure_patterns.get(pattern, 0))
            })
        
        # Sort by success rate
        best_times.sort(key=lambda x: x["success_rate"], reverse=True)
        analysis["best_times"] = best_times[:5]  # Top 5 best times
        
        # Save analysis
        analysis_file = Path("scheduled_runs/pattern_analysis.json")
        with open(analysis_file, "w") as f:
            json.dump(analysis, f, indent=2)
        
        # Generate recommendations
        if best_times:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            recommendations = ["# Scraping Timing Recommendations\n\n"]
            recommendations.append("Based on success patterns, the best times to run the scraper are:\n\n")
            
            for time_slot in best_times[:3]:
                day_name = days[time_slot["day"]]
                success_rate = time_slot["success_rate"] * 100
                recommendations.append(f"- **{day_name} at {time_slot['hour']:02d}:00** - {success_rate:.1f}% success rate\n")
            
            # Add tool recommendations
            if analysis["tools_used"]:
                recommendations.append("\n## Most Effective Tools\n\n")
                tools_sorted = sorted(analysis["tools_used"].items(), key=lambda x: x[1], reverse=True)
                for tool, count in tools_sorted:
                    recommendations.append(f"- **{tool}**: Used in {count} successful runs\n")
            
            recommendations_file = Path("scheduled_runs/recommendations.md")
            with open(recommendations_file, "w") as f:
                f.writelines(recommendations)
    
    def run_scheduler(self):
        """Run the scheduler continuously."""
        logger.info("Starting scheduler")
        
        # Run initial job immediately
        self.run_scraper_job()
        
        # Then run according to schedule
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

async def test_run():
    """Run a single test of the scheduled scraper."""
    scraper = ScheduledScraper()
    result = await scraper.run_scraper_with_tool("bridge construction", "NSW")
    return result

def main():
    """Main function to run the scheduled scraper."""
    parser = argparse.ArgumentParser(description="Scheduled Austender Scraper")
    parser.add_argument("--test", action="store_true", help="Run a single test")
    parser.add_argument("--keywords", type=str, help="Comma-separated list of keywords to search for")
    parser.add_argument("--states", type=str, help="Comma-separated list of states to filter by")
    parser.add_argument("--times", type=str, default="06:00,09:00,12:00,15:00,18:00,21:00,00:00,03:00",
                       help="Comma-separated list of times to run the scraper")
    parser.add_argument("--no-firecrawl", action="store_true", help="Disable Firecrawl integration")
    parser.add_argument("--use-proxy", action="store_true", help="Enable proxy usage")
    
    args = parser.parse_args()
    
    # Parse arguments
    config = {
        "schedule_times": args.times.split(","),
        "use_firecrawl": not args.no_firecrawl,
        "use_proxy": args.use_proxy
    }
    
    if args.keywords:
        config["keywords"] = [k.strip() for k in args.keywords.split(",")]
    
    if args.states:
        config["states"] = [s.strip() for s in args.states.split(",")]
    
    if args.test:
        # Run a single test
        print("Running test scraper job...")
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(test_run())
        print(f"Test completed with success: {result['success']}")
        if result['success']:
            print(f"Extracted {result['data_count']} items using {result['tool_used']}")
    else:
        # Run the scheduler
        scraper = ScheduledScraper(config)
        scraper.setup_schedule()
        scraper.run_scheduler()

if __name__ == "__main__":
    main()
