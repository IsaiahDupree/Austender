"""
Main Application Entry Point

This script initializes and runs the complete application, including:
- Setting up the database
- Starting the API server
- Initializing the scheduler for automated tasks
"""

import os
import sys
import logging
import threading
import argparse
import uvicorn
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/main.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

# Load environment variables
load_dotenv()

# Import database models and setup function
from database.models import setup_database

# Import scheduler
from scripts.scheduler import run_scheduler, run_on_demand

def run_api_server():
    """Run the FastAPI server"""
    logger.info("Starting API server")
    uvicorn.run(
        "api.app:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True, 
        log_level="info"
    )

def run_frontend_dev_server():
    """Run the React frontend development server"""
    logger.info("Starting frontend development server")
    os.chdir("frontend")
    os.system("npm start")
    os.chdir("..")

def main():
    """Main entry point for the application"""
    parser = argparse.ArgumentParser(description="Government Construction Opportunities Platform")
    parser.add_argument("--init-db", action="store_true", help="Initialize the database and exit")
    parser.add_argument("--run-scraper", action="store_true", help="Run the scraper once and exit")
    parser.add_argument("--api-only", action="store_true", help="Run only the API server")
    parser.add_argument("--scheduler-only", action="store_true", help="Run only the scheduler")
    parser.add_argument("--frontend-only", action="store_true", help="Run only the frontend development server")
    
    args = parser.parse_args()
    
    # Initialize the database
    logger.info("Initializing database")
    engine = setup_database()
    logger.info("Database initialized")
    
    if args.init_db:
        logger.info("Database initialization complete, exiting")
        return
    
    if args.run_scraper:
        logger.info("Running scraper once")
        run_on_demand()
        logger.info("Scraper run complete, exiting")
        return
    
    if args.api_only:
        run_api_server()
        return
    
    if args.scheduler_only:
        run_scheduler()
        return
    
    if args.frontend_only:
        run_frontend_dev_server()
        return
    
    # Run all components in parallel
    logger.info("Starting all application components")
    
    # Start scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    logger.info("Scheduler started in background thread")
    
    # Run API server in the main thread
    run_api_server()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1)
