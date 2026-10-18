"""
Scraper Scheduler Module

This module handles the scheduling of scraper jobs to automatically find new opportunities
from various sources at regular intervals.
"""

import os
import logging
import datetime
from typing import List, Dict, Any, Optional

# Import configuration and utilities
from config.config import UPDATE_INTERVAL_DAYS
from utils.logging_config import setup_logging
from utils.scheduler import scheduler
from utils.notification_coordinator import notification_coordinator

# Import scrapers
try:
    from scrapers.austender_scraper import AustenderScraper
    from scrapers.ani_scraper import ANIScraper
    from scrapers.icn_scraper import ICNScraper
    from scrapers.sam_scraper import SAMScraper
    SCRAPERS_AVAILABLE = True
except ImportError:
    SCRAPERS_AVAILABLE = False

# Set up logger
logger = setup_logging(__name__)


class ScraperScheduler:
    """
    Manages the scheduling of scraper jobs to automatically find new opportunities.
    
    This class handles setting up regular scraping of various opportunity sources
    and triggering notifications when new opportunities are found.
    """
    
    def __init__(self):
        """Initialize the scraper scheduler."""
        self.scheduler = scheduler
        self.notification_coordinator = notification_coordinator
        self._scrapers = {}
        self._last_run = {}
        
        # Initialize scrapers if available
        if SCRAPERS_AVAILABLE:
            self._initialize_scrapers()
        else:
            logger.warning("Scrapers not available. Only AustenderScraper will be initialized.")
            try:
                from scrapers.austender_scraper import AustenderScraper
                self._scrapers["austender"] = AustenderScraper()
            except ImportError:
                logger.error("AustenderScraper could not be imported. No scrapers available.")
    
    def _initialize_scrapers(self):
        """Initialize all available scrapers."""
        try:
            self._scrapers["austender"] = AustenderScraper()
            self._scrapers["ani"] = ANIScraper()
            self._scrapers["icn"] = ICNScraper()
            self._scrapers["sam"] = SAMScraper()
            logger.info(f"Initialized {len(self._scrapers)} scrapers")
        except Exception as e:
            logger.error(f"Error initializing scrapers: {str(e)}")
    
    def schedule_scraper_jobs(self):
        """Schedule regular scraper jobs."""
        # Schedule Austender scraper (higher priority, runs more frequently)
        if "austender" in self._scrapers:
            self.scheduler.add_job(
                job_id="austender_scraper",
                func=self.run_austender_scraper,
                interval_days=max(1, UPDATE_INTERVAL_DAYS // 2)  # Run more frequently
            )
            logger.info("Scheduled Austender scraper job")
        
        # Schedule other scrapers
        for source, scraper in self._scrapers.items():
            if source != "austender":
                self.scheduler.add_job(
                    job_id=f"{source}_scraper",
                    func=self.run_scraper,
                    interval_days=UPDATE_INTERVAL_DAYS,
                    args=[source]
                )
                logger.info(f"Scheduled {source} scraper job")
        
        # Schedule a job to run all scrapers once at startup (delayed by 2 minutes)
        self.scheduler.add_job(
            job_id="initial_scrape",
            func=self.run_all_scrapers,
            interval_minutes=2,  # Run once after 2 minutes, then remove
        )
        logger.info("Scheduled initial scrape job")
    
    def run_austender_scraper(self):
        """Run the Austender scraper job."""
        if "austender" not in self._scrapers:
            logger.error("Austender scraper not available")
            return
        
        logger.info("Running Austender scraper")
        try:
            scraper = self._scrapers["austender"]
            new_opportunities = scraper.run_full_scrape(
                categories=["construction"],
                max_pages=20
            )
            
            self._last_run["austender"] = datetime.datetime.now()
            
            # Process new opportunities for immediate notifications
            if new_opportunities:
                logger.info(f"Found {len(new_opportunities)} new opportunities from Austender")
                self._process_new_opportunities(new_opportunities)
            else:
                logger.info("No new opportunities found from Austender")
                
        except Exception as e:
            logger.error(f"Error running Austender scraper: {str(e)}", exc_info=True)
    
    def run_scraper(self, source):
        """
        Run a specific scraper job.
        
        Args:
            source (str): Source identifier (e.g., "ani", "icn", "sam")
        """
        if source not in self._scrapers:
            logger.error(f"Scraper for {source} not available")
            return
        
        logger.info(f"Running {source} scraper")
        try:
            scraper = self._scrapers[source]
            new_opportunities = scraper.run_full_scrape()
            
            self._last_run[source] = datetime.datetime.now()
            
            # Process new opportunities for immediate notifications
            if new_opportunities:
                logger.info(f"Found {len(new_opportunities)} new opportunities from {source}")
                self._process_new_opportunities(new_opportunities)
            else:
                logger.info(f"No new opportunities found from {source}")
                
        except Exception as e:
            logger.error(f"Error running {source} scraper: {str(e)}", exc_info=True)
    
    def run_all_scrapers(self):
        """Run all available scrapers."""
        logger.info("Running all scrapers")
        
        all_new_opportunities = []
        
        for source, scraper in self._scrapers.items():
            try:
                logger.info(f"Running {source} scraper")
                new_opportunities = scraper.run_full_scrape()
                
                self._last_run[source] = datetime.datetime.now()
                
                if new_opportunities:
                    logger.info(f"Found {len(new_opportunities)} new opportunities from {source}")
                    all_new_opportunities.extend(new_opportunities)
                else:
                    logger.info(f"No new opportunities found from {source}")
                    
            except Exception as e:
                logger.error(f"Error running {source} scraper: {str(e)}", exc_info=True)
        
        # Process all new opportunities together
        if all_new_opportunities:
            logger.info(f"Found {len(all_new_opportunities)} total new opportunities")
            self._process_new_opportunities(all_new_opportunities)
        else:
            logger.info("No new opportunities found from any source")
        
        # Remove this job after first run (it was just to do an initial scrape)
        logger.info("Removing initial scrape job after first run")
        self.scheduler.remove_job("initial_scrape")
    
    def _process_new_opportunities(self, opportunities):
        """
        Process new opportunities and trigger notifications.
        
        Args:
            opportunities (List[Dict]): List of new opportunities
        """
        # Send to notification coordinator for immediate notification processing
        try:
            for opportunity in opportunities:
                self.notification_coordinator.process_new_opportunity_immediate(opportunity)
            logger.info(f"Processed {len(opportunities)} opportunities for notifications")
        except Exception as e:
            logger.error(f"Error processing opportunities for notifications: {str(e)}", exc_info=True)
    
    def get_last_run_times(self):
        """
        Get the last run times for all scrapers.
        
        Returns:
            Dict[str, datetime]: Dictionary mapping source to last run time
        """
        return self._last_run
    
    def start(self):
        """Start the scraper scheduler."""
        # Schedule the scraper jobs
        self.schedule_scraper_jobs()
        
        # Start the scheduler if not already running
        if not self.scheduler.is_running:
            self.scheduler.start()
        
        logger.info("Scraper scheduler started")
    
    def stop(self):
        """Stop the scraper scheduler."""
        # Remove all scraper jobs
        for source in self._scrapers.keys():
            self.scheduler.remove_job(f"{source}_scraper")
        
        logger.info("Scraper scheduler stopped")


# Create a singleton instance
_scraper_scheduler_instance = None

def get_scraper_scheduler():
    """Get the global scraper scheduler instance."""
    global _scraper_scheduler_instance
    if _scraper_scheduler_instance is None:
        _scraper_scheduler_instance = ScraperScheduler()
    return _scraper_scheduler_instance

# Initialize the scraper scheduler
scraper_scheduler = get_scraper_scheduler()


def start_scraper_scheduler():
    """Start the scraper scheduler."""
    scheduler_instance = get_scraper_scheduler()
    scheduler_instance.start()


def stop_scraper_scheduler():
    """Stop the scraper scheduler."""
    scheduler_instance = get_scraper_scheduler()
    scheduler_instance.stop()
