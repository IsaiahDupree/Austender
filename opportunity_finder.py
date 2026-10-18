#!/usr/bin/env python
"""
Construction Opportunity Finder

This script helps find construction opportunities from multiple sources by:
1. Supporting manual entry of opportunities from browsing sessions
2. Maintaining a database of previously found opportunities 
3. Providing a simple interface to search and filter opportunities
4. Generating reports of new opportunities for notification purposes
"""

import os
import sys
import json
import datetime
import logging
import argparse
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/opportunity_finder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("opportunity_finder")

# Directory for storing opportunity data
DATA_DIR = Path(__file__).parent / "data" / "opportunities"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# SQLite database for opportunities
DB_PATH = DATA_DIR / "opportunities.db"


class OpportunityDatabase:
    """Database interface for managing construction opportunities."""
    
    def __init__(self, db_path: Path = DB_PATH):
        """Initialize the database connection."""
        self.db_path = db_path
        self._create_tables_if_needed()
    
    def _create_tables_if_needed(self):
        """Create the database tables if they don't exist."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            
            # Create opportunities table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                reference_id TEXT,
                url TEXT,
                source TEXT,
                publish_date TEXT,
                closing_date TEXT,
                location TEXT,
                category TEXT,
                subcategory TEXT,
                capital_value REAL,
                description TEXT,
                contact_name TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                procurement_method TEXT,
                scrape_date TEXT,
                is_notified INTEGER DEFAULT 0,
                UNIQUE(reference_id, source)
            )
            ''')
            
            # Create attachments table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY,
                opportunity_id INTEGER,
                name TEXT,
                url TEXT,
                description TEXT,
                upload_date TEXT,
                FOREIGN KEY (opportunity_id) REFERENCES opportunities (id)
            )
            ''')
            
            conn.commit()
    
    def add_opportunity(self, opportunity: Dict[str, Any]) -> int:
        """
        Add a new opportunity to the database.
        
        Args:
            opportunity: Dictionary containing opportunity data
            
        Returns:
            ID of the inserted opportunity, or -1 if failed
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Extract attachment data if present
                attachments = opportunity.pop("attachments", [])
                
                # Prepare date fields
                for date_field in ["publish_date", "closing_date", "scrape_date"]:
                    if date_field in opportunity and isinstance(opportunity[date_field], datetime.date):
                        opportunity[date_field] = opportunity[date_field].isoformat()
                
                # Check if the opportunity already exists
                existing_id = None
                if "reference_id" in opportunity and opportunity["reference_id"]:
                    cursor.execute(
                        "SELECT id FROM opportunities WHERE reference_id = ? AND source = ?", 
                        (opportunity["reference_id"], opportunity.get("source", ""))
                    )
                    result = cursor.fetchone()
                    if result:
                        existing_id = result[0]
                
                if existing_id:
                    # Update existing opportunity
                    placeholders = ", ".join([f"{k} = ?" for k in opportunity.keys()])
                    query = f"UPDATE opportunities SET {placeholders} WHERE id = ?"
                    cursor.execute(query, list(opportunity.values()) + [existing_id])
                    opportunity_id = existing_id
                else:
                    # Insert new opportunity
                    placeholders = ", ".join(["?"] * len(opportunity))
                    columns = ", ".join(opportunity.keys())
                    query = f"INSERT INTO opportunities ({columns}) VALUES ({placeholders})"
                    cursor.execute(query, list(opportunity.values()))
                    opportunity_id = cursor.lastrowid
                
                # Add attachments if present
                if attachments and opportunity_id:
                    for attachment in attachments:
                        # Prepare date fields
                        if "upload_date" in attachment and isinstance(attachment["upload_date"], datetime.date):
                            attachment["upload_date"] = attachment["upload_date"].isoformat()
                        
                        # Add opportunity_id
                        attachment["opportunity_id"] = opportunity_id
                        
                        # Insert attachment
                        placeholders = ", ".join(["?"] * len(attachment))
                        columns = ", ".join(attachment.keys())
                        query = f"INSERT INTO attachments ({columns}) VALUES ({placeholders})"
                        cursor.execute(query, list(attachment.values()))
                
                conn.commit()
                return opportunity_id
        
        except Exception as e:
            logger.error(f"Error adding opportunity: {str(e)}")
            return -1
    
    def get_opportunity(self, opportunity_id: int) -> Optional[Dict[str, Any]]:
        """
        Get an opportunity by ID.
        
        Args:
            opportunity_id: ID of the opportunity to retrieve
            
        Returns:
            Opportunity data or None if not found
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get opportunity
                cursor.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                # Convert to dictionary
                opportunity = dict(row)
                
                # Get attachments
                cursor.execute("SELECT * FROM attachments WHERE opportunity_id = ?", (opportunity_id,))
                attachments = [dict(row) for row in cursor.fetchall()]
                
                # Add attachments to opportunity
                opportunity["attachments"] = attachments
                
                return opportunity
                
        except Exception as e:
            logger.error(f"Error getting opportunity: {str(e)}")
            return None
    
    def search_opportunities(self, 
                           keywords: Optional[str] = None, 
                           source: Optional[str] = None,
                           location: Optional[str] = None,
                           category: Optional[str] = None,
                           min_date: Optional[datetime.date] = None,
                           max_date: Optional[datetime.date] = None,
                           min_value: Optional[float] = None,
                           max_value: Optional[float] = None,
                           limit: int = 100,
                           offset: int = 0) -> List[Dict[str, Any]]:
        """
        Search for opportunities based on criteria.
        
        Args:
            keywords: Keywords to search in title and description
            source: Source to filter by
            location: Location to filter by
            category: Category to filter by
            min_date: Minimum publish date
            max_date: Maximum publish date
            min_value: Minimum capital value
            max_value: Maximum capital value
            limit: Maximum number of results to return
            offset: Offset for pagination
            
        Returns:
            List of matching opportunities
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Build query
                query = "SELECT * FROM opportunities WHERE 1=1"
                params = []
                
                if keywords:
                    query += " AND (title LIKE ? OR description LIKE ?)"
                    search_term = f"%{keywords}%"
                    params.extend([search_term, search_term])
                
                if source:
                    query += " AND source = ?"
                    params.append(source)
                
                if location:
                    query += " AND location LIKE ?"
                    params.append(f"%{location}%")
                
                if category:
                    query += " AND category LIKE ?"
                    params.append(f"%{category}%")
                
                if min_date:
                    query += " AND publish_date >= ?"
                    params.append(min_date.isoformat())
                
                if max_date:
                    query += " AND publish_date <= ?"
                    params.append(max_date.isoformat())
                
                if min_value is not None:
                    query += " AND capital_value >= ?"
                    params.append(min_value)
                
                if max_value is not None:
                    query += " AND capital_value <= ?"
                    params.append(max_value)
                
                # Add sorting and pagination
                query += " ORDER BY publish_date DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                # Execute query
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # Convert to dictionaries
                opportunities = []
                for row in rows:
                    opportunity = dict(row)
                    
                    # Get attachments
                    cursor.execute("SELECT * FROM attachments WHERE opportunity_id = ?", (opportunity["id"],))
                    attachments = [dict(row) for row in cursor.fetchall()]
                    
                    # Add attachments to opportunity
                    opportunity["attachments"] = attachments
                    
                    opportunities.append(opportunity)
                
                return opportunities
                
        except Exception as e:
            logger.error(f"Error searching opportunities: {str(e)}")
            return []
    
    def get_new_opportunities(self, days: int = 1) -> List[Dict[str, Any]]:
        """
        Get opportunities added in the last X days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of new opportunities
        """
        cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).date()
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get opportunities added since cutoff date
                cursor.execute(
                    "SELECT * FROM opportunities WHERE scrape_date >= ? ORDER BY scrape_date DESC",
                    (cutoff_date.isoformat(),)
                )
                rows = cursor.fetchall()
                
                # Convert to dictionaries
                opportunities = []
                for row in rows:
                    opportunity = dict(row)
                    
                    # Get attachments
                    cursor.execute("SELECT * FROM attachments WHERE opportunity_id = ?", (opportunity["id"],))
                    attachments = [dict(row) for row in cursor.fetchall()]
                    
                    # Add attachments to opportunity
                    opportunity["attachments"] = attachments
                    
                    opportunities.append(opportunity)
                
                return opportunities
                
        except Exception as e:
            logger.error(f"Error getting new opportunities: {str(e)}")
            return []
    
    def mark_as_notified(self, opportunity_id: int) -> bool:
        """
        Mark an opportunity as having been included in a notification.
        
        Args:
            opportunity_id: ID of the opportunity to mark
            
        Returns:
            Whether the update was successful
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE opportunities SET is_notified = 1 WHERE id = ?",
                    (opportunity_id,)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error marking opportunity as notified: {str(e)}")
            return False
    
    def get_unnotified_opportunities(self) -> List[Dict[str, Any]]:
        """
        Get opportunities that haven't been included in notifications yet.
        
        Returns:
            List of unnotified opportunities
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT * FROM opportunities WHERE is_notified = 0 ORDER BY publish_date DESC"
                )
                rows = cursor.fetchall()
                
                # Convert to dictionaries
                opportunities = []
                for row in rows:
                    opportunity = dict(row)
                    
                    # Get attachments
                    cursor.execute("SELECT * FROM attachments WHERE opportunity_id = ?", (opportunity["id"],))
                    attachments = [dict(row) for row in cursor.fetchall()]
                    
                    # Add attachments to opportunity
                    opportunity["attachments"] = attachments
                    
                    opportunities.append(opportunity)
                
                return opportunities
                
        except Exception as e:
            logger.error(f"Error getting unnotified opportunities: {str(e)}")
            return []


def add_manual_opportunity():
    """Interactive function to manually add an opportunity."""
    print("\n=== Add Manual Opportunity ===\n")
    
    opportunity = {}
    
    # Basic information
    opportunity["title"] = input("Title: ")
    opportunity["reference_id"] = input("Reference ID: ")
    opportunity["url"] = input("URL: ")
    opportunity["source"] = input("Source (e.g., Austender, NSW eTender): ")
    
    # Dates
    publish_date_str = input("Publish Date (YYYY-MM-DD): ")
    if publish_date_str:
        try:
            opportunity["publish_date"] = datetime.date.fromisoformat(publish_date_str)
        except ValueError:
            print("Invalid date format. Using today's date.")
            opportunity["publish_date"] = datetime.date.today()
    
    closing_date_str = input("Closing Date (YYYY-MM-DD): ")
    if closing_date_str:
        try:
            opportunity["closing_date"] = datetime.date.fromisoformat(closing_date_str)
        except ValueError:
            print("Invalid date format. Leaving blank.")
    
    # Other details
    opportunity["location"] = input("Location: ")
    opportunity["category"] = input("Category: ")
    opportunity["subcategory"] = input("Subcategory: ")
    
    value_str = input("Capital Value: ")
    if value_str:
        try:
            opportunity["capital_value"] = float(value_str.replace(",", "").replace("$", ""))
        except ValueError:
            print("Invalid value format. Leaving blank.")
    
    opportunity["description"] = input("Description: ")
    
    # Contact information
    opportunity["contact_name"] = input("Contact Name: ")
    opportunity["contact_email"] = input("Contact Email: ")
    opportunity["contact_phone"] = input("Contact Phone: ")
    
    # Procurement method
    opportunity["procurement_method"] = input("Procurement Method: ")
    
    # Set scrape date to today
    opportunity["scrape_date"] = datetime.date.today()
    
    # Attachments
    attachments = []
    while True:
        print("\nAdd Attachment (leave name blank to stop)")
        name = input("Name: ")
        
        if not name:
            break
        
        attachment = {
            "name": name,
            "url": input("URL: "),
            "description": input("Description: "),
            "upload_date": datetime.date.today()
        }
        
        attachments.append(attachment)
    
    if attachments:
        opportunity["attachments"] = attachments
    
    # Add to database
    db = OpportunityDatabase()
    opportunity_id = db.add_opportunity(opportunity)
    
    if opportunity_id > 0:
        print(f"\nOpportunity added successfully with ID: {opportunity_id}")
    else:
        print("\nFailed to add opportunity")


def search_opportunities(args):
    """Search for opportunities based on command-line arguments."""
    db = OpportunityDatabase()
    
    # Parse dates if provided
    min_date = None
    if args.min_date:
        try:
            min_date = datetime.date.fromisoformat(args.min_date)
        except ValueError:
            print(f"Invalid min_date format: {args.min_date}. Should be YYYY-MM-DD.")
    
    max_date = None
    if args.max_date:
        try:
            max_date = datetime.date.fromisoformat(args.max_date)
        except ValueError:
            print(f"Invalid max_date format: {args.max_date}. Should be YYYY-MM-DD.")
    
    # Search for opportunities
    opportunities = db.search_opportunities(
        keywords=args.keywords,
        source=args.source,
        location=args.location,
        category=args.category,
        min_date=min_date,
        max_date=max_date,
        min_value=args.min_value,
        max_value=args.max_value,
        limit=args.limit,
        offset=args.offset
    )
    
    print(f"\nFound {len(opportunities)} matching opportunities:")
    
    for i, opp in enumerate(opportunities, 1):
        print(f"\n{'-'*80}")
        print(f"Opportunity {i}/{len(opportunities)}:")
        print(f"{'-'*80}")
        print(f"ID:            {opp.get('id')}")
        print(f"Title:         {opp.get('title', 'Not specified')}")
        print(f"Reference ID:  {opp.get('reference_id', 'Not specified')}")
        print(f"Source:        {opp.get('source', 'Not specified')}")
        print(f"Location:      {opp.get('location', 'Not specified')}")
        print(f"Category:      {opp.get('category', 'Not specified')}")
        
        if opp.get('publish_date'):
            print(f"Published:     {opp.get('publish_date')}")
        
        if opp.get('closing_date'):
            print(f"Closing:       {opp.get('closing_date')}")
        
        if opp.get('capital_value'):
            print(f"Value:         ${opp.get('capital_value'):,.2f}")
        
        if opp.get('url'):
            print(f"URL:           {opp.get('url')}")
        
        # Show attachments if available and detailed output is requested
        if args.details and opp.get('attachments'):
            print("\nAttachments:")
            for j, attachment in enumerate(opp.get('attachments', []), 1):
                print(f"  {j}. {attachment.get('name', 'No name')}")
                print(f"     URL: {attachment.get('url', 'No URL')}")
        
        # Show description if available and detailed output is requested
        if args.details and opp.get('description'):
            print("\nDescription:")
            print(opp.get('description'))
    
    if args.export:
        export_opportunities(opportunities, args.export)


def export_opportunities(opportunities, filename):
    """Export opportunities to a CSV file."""
    if not opportunities:
        print("No opportunities to export")
        return
    
    if not filename.endswith('.csv'):
        filename += '.csv'
    
    try:
        with open(filename, 'w', newline='') as f:
            # Determine fields to export
            fields = [
                'id', 'title', 'reference_id', 'url', 'source', 'publish_date',
                'closing_date', 'location', 'category', 'subcategory',
                'capital_value', 'description', 'contact_name', 'contact_email',
                'contact_phone', 'procurement_method', 'scrape_date'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            
            for opp in opportunities:
                # Extract only the fields we want
                row = {field: opp.get(field, '') for field in fields}
                writer.writerow(row)
        
        print(f"\nExported {len(opportunities)} opportunities to {filename}")
    
    except Exception as e:
        print(f"Error exporting opportunities: {str(e)}")


def get_new_opportunities(args):
    """Get opportunities added in the last X days."""
    db = OpportunityDatabase()
    opportunities = db.get_new_opportunities(days=args.days)
    
    print(f"\nFound {len(opportunities)} opportunities added in the last {args.days} days:")
    
    for i, opp in enumerate(opportunities, 1):
        print(f"\n{'-'*80}")
        print(f"Opportunity {i}/{len(opportunities)}:")
        print(f"{'-'*80}")
        print(f"ID:            {opp.get('id')}")
        print(f"Title:         {opp.get('title', 'Not specified')}")
        print(f"Reference ID:  {opp.get('reference_id', 'Not specified')}")
        print(f"Source:        {opp.get('source', 'Not specified')}")
        print(f"Location:      {opp.get('location', 'Not specified')}")
        
        if opp.get('publish_date'):
            print(f"Published:     {opp.get('publish_date')}")
        
        if opp.get('closing_date'):
            print(f"Closing:       {opp.get('closing_date')}")
        
        if opp.get('capital_value'):
            print(f"Value:         ${opp.get('capital_value'):,.2f}")
        
        if opp.get('url'):
            print(f"URL:           {opp.get('url')}")
    
    if args.export:
        export_opportunities(opportunities, args.export)


def get_unnotified_opportunities(args):
    """Get opportunities that haven't been included in notifications yet."""
    db = OpportunityDatabase()
    opportunities = db.get_unnotified_opportunities()
    
    print(f"\nFound {len(opportunities)} unnotified opportunities:")
    
    for i, opp in enumerate(opportunities, 1):
        print(f"\n{'-'*80}")
        print(f"Opportunity {i}/{len(opportunities)}:")
        print(f"{'-'*80}")
        print(f"ID:            {opp.get('id')}")
        print(f"Title:         {opp.get('title', 'Not specified')}")
        print(f"Reference ID:  {opp.get('reference_id', 'Not specified')}")
        print(f"Source:        {opp.get('source', 'Not specified')}")
        print(f"Location:      {opp.get('location', 'Not specified')}")
        
        if opp.get('publish_date'):
            print(f"Published:     {opp.get('publish_date')}")
        
        if opp.get('closing_date'):
            print(f"Closing:       {opp.get('closing_date')}")
        
        if opp.get('capital_value'):
            print(f"Value:         ${opp.get('capital_value'):,.2f}")
        
        if opp.get('url'):
            print(f"URL:           {opp.get('url')}")
    
    if args.export:
        export_opportunities(opportunities, args.export)
    
    if args.mark_notified:
        for opp in opportunities:
            db.mark_as_notified(opp['id'])
        print(f"\nMarked {len(opportunities)} opportunities as notified")


def mark_as_notified(args):
    """Mark an opportunity as having been included in a notification."""
    db = OpportunityDatabase()
    success = db.mark_as_notified(args.id)
    
    if success:
        print(f"Opportunity {args.id} marked as notified")
    else:
        print(f"Failed to mark opportunity {args.id} as notified")


def main():
    """Main function to parse arguments and run the appropriate action."""
    parser = argparse.ArgumentParser(description="Construction Opportunity Finder")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Add manual opportunity
    add_parser = subparsers.add_parser("add", help="Add a manual opportunity")
    add_parser.set_defaults(func=lambda args: add_manual_opportunity())
    
    # Search opportunities
    search_parser = subparsers.add_parser("search", help="Search for opportunities")
    search_parser.add_argument("--keywords", help="Keywords to search in title and description")
    search_parser.add_argument("--source", help="Source to filter by")
    search_parser.add_argument("--location", help="Location to filter by")
    search_parser.add_argument("--category", help="Category to filter by")
    search_parser.add_argument("--min-date", help="Minimum publish date (YYYY-MM-DD)")
    search_parser.add_argument("--max-date", help="Maximum publish date (YYYY-MM-DD)")
    search_parser.add_argument("--min-value", type=float, help="Minimum capital value")
    search_parser.add_argument("--max-value", type=float, help="Maximum capital value")
    search_parser.add_argument("--limit", type=int, default=100, help="Maximum number of results to return")
    search_parser.add_argument("--offset", type=int, default=0, help="Offset for pagination")
    search_parser.add_argument("--details", action="store_true", help="Show detailed information")
    search_parser.add_argument("--export", help="Export results to a CSV file")
    search_parser.set_defaults(func=search_opportunities)
    
    # Get new opportunities
    new_parser = subparsers.add_parser("new", help="Get opportunities added in the last X days")
    new_parser.add_argument("--days", type=int, default=1, help="Number of days to look back")
    new_parser.add_argument("--export", help="Export results to a CSV file")
    new_parser.set_defaults(func=get_new_opportunities)
    
    # Get unnotified opportunities
    unnotified_parser = subparsers.add_parser("unnotified", help="Get opportunities that haven't been notified yet")
    unnotified_parser.add_argument("--export", help="Export results to a CSV file")
    unnotified_parser.add_argument("--mark-notified", action="store_true", help="Mark opportunities as notified")
    unnotified_parser.set_defaults(func=get_unnotified_opportunities)
    
    # Mark as notified
    mark_parser = subparsers.add_parser("mark", help="Mark an opportunity as notified")
    mark_parser.add_argument("id", type=int, help="ID of the opportunity to mark")
    mark_parser.set_defaults(func=mark_as_notified)
    
    args = parser.parse_args()
    
    # Run the appropriate function
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
