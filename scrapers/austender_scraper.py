"""
Austender Scraper Module

This module is responsible for scraping construction opportunities from the Austender website.
It includes functions to search, parse, and store the data in our database.
"""

import requests
from bs4 import BeautifulSoup
import datetime
import logging
import time
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Opportunity, Attachment
from config.config import (
    AUSTENDER_URL, USER_AGENT, REQUEST_TIMEOUT, 
    RETRY_COUNT, RETRY_DELAY, DATABASE_URL
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/austender_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("austender_scraper")

# Set up database connection
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class AustenderScraper:
    """Scraper class for Austender website."""
    
    def __init__(self):
        """Initialize the scraper with default configuration."""
        self.base_url = AUSTENDER_URL
        self.search_url = f"{self.base_url}/search/search-advanced.aspx"
        self.headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    @retry(stop=stop_after_attempt(RETRY_COUNT), wait=wait_exponential(multiplier=1, min=RETRY_DELAY, max=RETRY_DELAY*3))
    def get_page(self, url: str) -> BeautifulSoup:
        """
        Fetch a page and return its BeautifulSoup representation.
        
        Args:
            url (str): The URL to fetch
            
        Returns:
            BeautifulSoup: Parsed HTML content
            
        Raises:
            Exception: If the request fails after retries
        """
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch page {url}: {str(e)}")
            raise
    
    def search_opportunities(self, 
                            category: Optional[str] = "construction", 
                            keyword: Optional[str] = None,
                            location: Optional[str] = None,
                            date_from: Optional[datetime.date] = None,
                            date_to: Optional[datetime.date] = None,
                            min_value: Optional[float] = None,
                            max_value: Optional[float] = None,
                            page: int = 1,
                            ) -> List[Dict[str, Any]]:
        """
        Search for opportunities based on given criteria.
        
        Args:
            category (str, optional): Category of opportunities
            keyword (str, optional): Keyword to search for
            location (str, optional): Location to filter by
            date_from (datetime.date, optional): Start date for publishing
            date_to (datetime.date, optional): End date for publishing
            min_value (float, optional): Minimum contract value
            max_value (float, optional): Maximum contract value
            page (int): Page number to fetch
            
        Returns:
            List[Dict[str, Any]]: List of opportunity summary dictionaries
        """
        # Building search parameters
        params = {
            "category": category or "",
            "keyword": keyword or "",
            "location": location or "", 
            "page": page,
        }
        
        if date_from:
            params["dateFrom"] = date_from.strftime("%d/%m/%Y")
        
        if date_to:
            params["dateTo"] = date_to.strftime("%d/%m/%Y")
            
        if min_value:
            params["minValue"] = str(min_value)
            
        if max_value:
            params["maxValue"] = str(max_value)
        
        # This URL structure is hypothetical and should be adjusted based on actual Austender search parameters
        search_url = f"{self.search_url}?{'&'.join([f'{k}={v}' for k, v in params.items() if v])}"
        
        logger.info(f"Searching for opportunities with URL: {search_url}")
        
        try:
            soup = self.get_page(search_url)
            results = self._parse_search_results(soup)
            logger.info(f"Found {len(results)} opportunities on page {page}")
            return results
        except Exception as e:
            logger.error(f"Error searching for opportunities: {str(e)}")
            return []
    
    def _parse_search_results(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Parse the search results from the BeautifulSoup object.
        
        Args:
            soup (BeautifulSoup): The parsed HTML of the search results page
            
        Returns:
            List[Dict[str, Any]]: List of parsed opportunity summaries
        """
        results = []
        
        # This is a placeholder implementation that should be adjusted based on actual HTML structure
        opportunity_elements = soup.select(".opportunity-item")  # Adjust selector based on actual HTML
        
        for element in opportunity_elements:
            try:
                # Extract basic information
                title_element = element.select_one(".title")
                id_element = element.select_one(".reference-id")
                dates_element = element.select_one(".dates")
                value_element = element.select_one(".value")
                location_element = element.select_one(".location")
                
                # Create an opportunity object with extracted data
                opportunity = {
                    "title": title_element.text.strip() if title_element else None,
                    "reference_id": id_element.text.strip() if id_element else None,
                    "url": self.base_url + title_element.get("href") if title_element and title_element.get("href") else None,
                    "publish_date": self._parse_date(dates_element.select_one(".publish-date").text.strip()) if dates_element and dates_element.select_one(".publish-date") else None,
                    "closing_date": self._parse_date(dates_element.select_one(".closing-date").text.strip()) if dates_element and dates_element.select_one(".closing-date") else None,
                    "capital_value": self._parse_value(value_element.text.strip()) if value_element else None,
                    "location": location_element.text.strip() if location_element else None,
                }
                
                # Only add opportunities with valid data
                if opportunity["title"] and opportunity["url"]:
                    results.append(opportunity)
            except Exception as e:
                logger.warning(f"Error parsing opportunity element: {str(e)}")
                continue
        
        return results
    
    def get_opportunity_details(self, url: str) -> Dict[str, Any]:
        """
        Fetch and parse detailed information about an opportunity.
        
        Args:
            url (str): URL of the opportunity detail page
            
        Returns:
            Dict[str, Any]: Detailed opportunity information
        """
        logger.info(f"Fetching details for opportunity: {url}")
        
        try:
            soup = self.get_page(url)
            details = self._parse_opportunity_details(soup, url)
            return details
        except Exception as e:
            logger.error(f"Error fetching opportunity details: {str(e)}")
            return {}
    
    def _parse_opportunity_details(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Parse the opportunity details from the BeautifulSoup object.
        
        Args:
            soup (BeautifulSoup): The parsed HTML of the opportunity detail page
            url (str): URL of the opportunity detail page
            
        Returns:
            Dict[str, Any]: Detailed opportunity information
        """
        details = {
            "source": "Austender",
            "url": url,
        }
        
        try:
            # These selectors are placeholders and should be adjusted for actual HTML structure
            details["title"] = soup.select_one("h1.opportunity-title").text.strip()
            details["reference_id"] = soup.select_one(".atm-id").text.strip()
            details["description"] = soup.select_one(".opportunity-description").text.strip()
            
            # Extract dates
            publish_date = soup.select_one(".publish-date")
            closing_date = soup.select_one(".closing-date")
            start_date = soup.select_one(".start-date")
            
            if publish_date:
                details["publish_date"] = self._parse_date(publish_date.text.strip())
            if closing_date:
                details["closing_date"] = self._parse_date(closing_date.text.strip())
            if start_date:
                details["start_date"] = self._parse_date(start_date.text.strip())
            
            # Extract financial information
            value_element = soup.select_one(".estimated-value")
            if value_element:
                details["capital_value"] = self._parse_value(value_element.text.strip())
            
            # Extract category information
            category_element = soup.select_one(".category")
            if category_element:
                details["category"] = category_element.text.strip()
            
            # Extract procurement method
            procurement_method = soup.select_one(".procurement-method")
            if procurement_method:
                details["procurement_method"] = procurement_method.text.strip()
            
            # Extract panel information
            panel_element = soup.select_one(".panel-info")
            if panel_element:
                details["panel_arrangement"] = True
                details["panel_name"] = panel_element.text.strip()
            
            # Extract location information
            location_element = soup.select_one(".location")
            if location_element:
                details["location"] = location_element.text.strip()
            
            # Extract contact information
            contact_name = soup.select_one(".contact-name")
            contact_email = soup.select_one(".contact-email")
            contact_phone = soup.select_one(".contact-phone")
            
            if contact_name:
                details["contact_name"] = contact_name.text.strip()
            if contact_email:
                details["contact_email"] = contact_email.text.strip()
            if contact_phone:
                details["contact_phone"] = contact_phone.text.strip()
            
            # Extract attachments
            attachment_elements = soup.select(".attachment")
            attachments = []
            
            for attachment in attachment_elements:
                name_element = attachment.select_one(".name")
                url_element = attachment.select_one("a")
                description_element = attachment.select_one(".description")
                
                if name_element and url_element:
                    attachments.append({
                        "name": name_element.text.strip(),
                        "url": self.base_url + url_element.get("href") if not url_element.get("href").startswith("http") else url_element.get("href"),
                        "description": description_element.text.strip() if description_element else None,
                    })
            
            details["attachments"] = attachments
            
        except Exception as e:
            logger.error(f"Error parsing opportunity details: {str(e)}")
        
        return details
    
    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """
        Parse a date string into a datetime.date object.
        
        Args:
            date_str (str): Date string to parse
            
        Returns:
            Optional[datetime.date]: Parsed date or None if parsing fails
        """
        try:
            # Adjust the format based on actual date format used by Austender
            return datetime.datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError:
            try:
                return datetime.datetime.strptime(date_str, "%d %b %Y").date()
            except ValueError:
                logger.warning(f"Could not parse date: {date_str}")
                return None
    
    def _parse_value(self, value_str: str) -> Optional[float]:
        """
        Parse a monetary value string into a float.
        
        Args:
            value_str (str): Value string to parse
            
        Returns:
            Optional[float]: Parsed value or None if parsing fails
        """
        try:
            # Remove currency symbols, commas, etc. and convert to float
            cleaned_value = value_str.replace("$", "").replace(",", "").replace("AUD", "").strip()
            
            # Handle ranges like "100,000 - 200,000" by taking the average
            if "-" in cleaned_value:
                parts = cleaned_value.split("-")
                min_val = float(parts[0].strip())
                max_val = float(parts[1].strip())
                return (min_val + max_val) / 2
            
            return float(cleaned_value)
        except ValueError:
            logger.warning(f"Could not parse value: {value_str}")
            return None

    def save_opportunities(self, opportunities: List[Dict[str, Any]]) -> None:
        """
        Save a list of opportunities to the database.
        
        Args:
            opportunities (List[Dict[str, Any]]): List of opportunity dictionaries to save
        """
        with SessionLocal() as db:
            for opp_data in opportunities:
                try:
                    # Check if opportunity already exists
                    existing = db.query(Opportunity).filter_by(
                        reference_id=opp_data.get("reference_id"),
                        source="Austender"
                    ).first()
                    
                    if existing:
                        # Update existing opportunity
                        for key, value in opp_data.items():
                            if key != "attachments" and value is not None:
                                setattr(existing, key, value)
                        
                        existing.updated_at = datetime.datetime.now()
                        existing.last_scraped = datetime.datetime.now()
                        
                        # Handle attachments
                        if "attachments" in opp_data:
                            self._update_attachments(db, existing, opp_data["attachments"])
                            
                        logger.info(f"Updated opportunity: {existing.reference_id}")
                    else:
                        # Create new opportunity
                        attachments_data = opp_data.pop("attachments", [])
                        
                        new_opportunity = Opportunity(
                            **{k: v for k, v in opp_data.items() if k != "attachments"},
                            source="Austender",
                            created_at=datetime.datetime.now(),
                            last_scraped=datetime.datetime.now(),
                            is_active=True
                        )
                        
                        db.add(new_opportunity)
                        db.flush()  # Flush to get the ID without committing
                        
                        # Add attachments
                        self._add_attachments(db, new_opportunity, attachments_data)
                        
                        logger.info(f"Added new opportunity: {new_opportunity.reference_id}")
                    
                    db.commit()
                    
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error saving opportunity: {str(e)}")
    
    def _add_attachments(self, db: Session, opportunity: Opportunity, attachments_data: List[Dict[str, Any]]) -> None:
        """
        Add attachments to an opportunity.
        
        Args:
            db (Session): Database session
            opportunity (Opportunity): Opportunity to add attachments to
            attachments_data (List[Dict[str, Any]]): List of attachment dictionaries
        """
        for attachment_data in attachments_data:
            new_attachment = Attachment(
                opportunity_id=opportunity.id,
                name=attachment_data.get("name"),
                url=attachment_data.get("url"),
                description=attachment_data.get("description"),
                upload_date=datetime.date.today()
            )
            db.add(new_attachment)
    
    def _update_attachments(self, db: Session, opportunity: Opportunity, attachments_data: List[Dict[str, Any]]) -> None:
        """
        Update attachments for an opportunity.
        
        Args:
            db (Session): Database session
            opportunity (Opportunity): Opportunity to update attachments for
            attachments_data (List[Dict[str, Any]]): List of attachment dictionaries
        """
        # Get existing attachment URLs
        existing_urls = {attachment.url: attachment for attachment in opportunity.attachments}
        
        # Add new attachments
        for attachment_data in attachments_data:
            url = attachment_data.get("url")
            
            if url not in existing_urls:
                new_attachment = Attachment(
                    opportunity_id=opportunity.id,
                    name=attachment_data.get("name"),
                    url=url,
                    description=attachment_data.get("description"),
                    upload_date=datetime.date.today()
                )
                db.add(new_attachment)
    
    def run_full_scrape(self, 
                       categories: List[str] = ["construction"],
                       locations: List[str] = None,
                       max_pages: int = 10) -> None:
        """
        Run a full scrape of opportunities based on given criteria.
        
        Args:
            categories (List[str]): List of categories to scrape
            locations (List[str], optional): List of locations to scrape
            max_pages (int): Maximum number of pages to scrape per category/location
        """
        if not locations:
            locations = [None]  # Use None to indicate all locations
        
        for category in categories:
            for location in locations:
                logger.info(f"Starting scrape for category '{category}' and location '{location}'")
                
                for page in range(1, max_pages + 1):
                    opportunities = self.search_opportunities(
                        category=category,
                        location=location,
                        page=page
                    )
                    
                    if not opportunities:
                        logger.info(f"No more opportunities found for category '{category}' and location '{location}' after page {page}")
                        break
                    
                    # Fetch details for each opportunity
                    detailed_opportunities = []
                    for opp in opportunities:
                        if opp.get("url"):
                            details = self.get_opportunity_details(opp["url"])
                            detailed_opportunities.append(details)
                            # Be nice to the server
                            time.sleep(1)
                    
                    # Save opportunities to the database
                    self.save_opportunities(detailed_opportunities)
                    
                    logger.info(f"Processed page {page} for category '{category}' and location '{location}'")
                    # Be nice to the server
                    time.sleep(2)


# Main execution
if __name__ == "__main__":
    scraper = AustenderScraper()
    scraper.run_full_scrape()
