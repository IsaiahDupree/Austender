#!/usr/bin/env python3
"""
Run Focused ATM Scraper
-----------------------
Simple wrapper script to run the Focused ATM Scraper with command-line arguments
and provide user-friendly output.
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime
from focused_atm_scraper import FocusedATMScraper

async def run_scraper(args):
    """Run the Focused ATM Scraper with the provided arguments."""
    print(f"\n{'=' * 60}")
    print(f"AUSTENDER FOCUSED ATM SCRAPER")
    print(f"{'=' * 60}")
    print(f"Starting scraper with the following parameters:")
    print(f"  - Keyword: {args.keyword}")
    print(f"  - State: {args.state if args.state else 'All states'}")
    print(f"  - Headless mode: {'Enabled' if args.headless else 'Disabled'}")
    print(f"  - Debug mode: {'Enabled' if args.debug else 'Disabled'}")
    print(f"  - Output file: {args.output if args.output else 'Auto-generated timestamp'}")
    print(f"{'=' * 60}\n")
    
    # Initialize the scraper with all available options
    scraper = FocusedATMScraper(
        headless=args.headless, 
        debug=args.debug,
        slow_mo=args.slow_mo,
        max_retries=args.retries,
        model=args.model
    )
    
    # Set browser rotation and proxy if specified
    if args.no_browser_rotation:
        scraper.rotate_browsers = False
        
    # Set proxy if provided
    if args.proxy:
        os.environ["PROXY_SERVER"] = args.proxy
    
    try:
        # Start browser
        print("Starting browser...")
        await scraper.start_browser()
        
        # Navigate to ATM search page
        print("Navigating to ATM search page...")
        success = await scraper.execute_with_retries(scraper.navigate_to_atm_search)
        if not success:
            print("❌ Failed to navigate to ATM search page")
            return
        
        # Perform search
        print(f"Searching for ATMs with keyword '{args.keyword}'{f' in {args.state}' if args.state else ''}...")
        search_success = await scraper.execute_with_retries(
            scraper.search_atm, 
            keyword=args.keyword, 
            state=args.state
        )
        if not search_success:
            print("❌ Failed to perform ATM search")
            return
        
        # Extract listings
        print("Extracting ATM listings...")
        listings = await scraper.execute_with_retries(scraper.extract_atm_listings)
        
        # Output results summary
        if listings:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            print(f"\n✅ Successfully extracted {len(listings)} ATM listings")
            
            # Display first few listings as preview
            print("\nPreview of extracted listings:")
            for i, listing in enumerate(listings[:3]):
                print(f"\n--- Listing {i+1} ---")
                for key, value in listing.items():
                    if key != "URL" or args.debug:  # Only show URL in debug mode
                        print(f"{key}: {value}")
            
            if len(listings) > 3:
                print(f"\n... and {len(listings) - 3} more listings")
            
            # Custom output filename if provided
            if args.output:
                output_file = f"output/{args.output}_{timestamp}.json"
            else:
                output_file = f"output/atm_listings_{timestamp}.json"
            
            print(f"\nResults saved to: {output_file}")
            
        else:
            print("\n❌ No ATM listings were extracted")
            
        print(f"\n{'=' * 60}")
        print("SCRAPER EXECUTION COMPLETED")
        print(f"{'=' * 60}\n")
        
    except Exception as e:
        print(f"\n❌ Error in scraper execution: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Ensure browser is closed
        print("Closing browser...")
        await scraper.close()

def main():
    """Parse arguments and run the scraper."""
    parser = argparse.ArgumentParser(description="Run the Focused ATM Scraper for Austender")
    parser.add_argument("--keyword", type=str, default="construction", 
                        help="Keyword to search for (default: construction)")
    parser.add_argument("--state", type=str, 
                        help="State to filter by (e.g., NSW, VIC)")
    parser.add_argument("--headless", action="store_true", 
                        help="Run browser in headless mode")
    parser.add_argument("--debug", action="store_true", 
                        help="Enable debug mode with additional logging and outputs")
    parser.add_argument("--output", type=str, 
                        help="Custom output filename prefix (default is timestamped)")
    parser.add_argument("--slow-mo", type=int, default=100,
                        help="Slow motion delay in ms for browser actions (default: 100)")
    parser.add_argument("--retries", type=int, default=5, 
                        help="Maximum number of retries for operations (default: 5)")
    parser.add_argument("--proxy", type=str, 
                        help="Proxy server to use (format: http://user:pass@host:port)")
    parser.add_argument("--no-browser-rotation", action="store_true", 
                        help="Disable browser type rotation on retries")
    parser.add_argument("--browser-type", type=str, choices=["chromium", "firefox", "webkit"], 
                        default="chromium", help="Browser type to use initially")
    parser.add_argument("--model", type=str, default="gpt-4o", 
                        help="OpenAI model to use for screenshot analysis (default: gpt-4o)")
    
    args = parser.parse_args()
    
    # Run the scraper
    asyncio.run(run_scraper(args))

if __name__ == "__main__":
    main()
