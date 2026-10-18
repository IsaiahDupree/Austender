#!/usr/bin/env python
"""
Simple test script to verify Firecrawl API functionality
"""

import os
import json
import requests
import sys

# Get API key from environment or use the default test key
API_KEY = os.getenv("FIRECRAWL_API_KEY", __import__('os').environ['FIRECRAWL_API_KEY'])
BASE_URL = os.getenv("FIRECRAWL_BASE_URL", "http://localhost:3005")

def test_api_connection():
    """Test that the Firecrawl API is responsive"""
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code == 200:
            print(f"✅ API is responding at {BASE_URL}")
            return True
        else:
            print(f"❌ API returned status code {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error connecting to API: {str(e)}")
        return False

def test_simple_scrape():
    """Test a simple scrape of example.com"""
    url = f"{BASE_URL}/v1/scrape"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-Key": API_KEY
    }
    payload = {
        "url": "https://example.com"
    }
    
    try:
        print(f"Sending request to {url}")
        print(f"Headers: {json.dumps(headers, indent=2)}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Successfully scraped example.com")
            if result.get('success') and 'data' in result:
                data_keys = list(result['data'].keys())
                print(f"Data keys: {', '.join(data_keys)}")
                html_length = len(result['data'].get('html', '')) if 'html' in result['data'] else 0
                print(f"HTML length: {html_length} bytes")
            return True
        else:
            print(f"❌ API returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error during scrape: {str(e)}")
        return False

def test_austender_scrape():
    """Test scraping Austender"""
    url = f"{BASE_URL}/v1/scrape"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-Key": API_KEY
    }
    payload = {
        "url": "https://www.tenders.gov.au/Search/KeywordSearch?keyword=construction&type=ATM&dateType=ClosingDate",
        "options": {
            "waitForSelector": ".search-results .opportunity-item",
            "timeout": 60000
        }
    }
    
    try:
        print(f"\nSending request to {url} for Austender")
        print(f"Headers: {json.dumps(headers, indent=2)}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Successfully scraped Austender")
            if result.get('success') and 'data' in result:
                data_keys = list(result['data'].keys())
                print(f"Data keys: {', '.join(data_keys)}")
                html_length = len(result['data'].get('html', '')) if 'html' in result['data'] else 0
                print(f"HTML length: {html_length} bytes")
                
                # Save the HTML to a file for inspection
                if html_length > 0:
                    with open("austender_results.html", "w", encoding="utf-8") as f:
                        f.write(result['data']['html'])
                    print(f"Saved HTML to austender_results.html")
            else:
                print(f"❌ No success or data in response")
                print(f"Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ API returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error during scrape: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Firecrawl API integration\n")
    
    if not test_api_connection():
        print("Cannot proceed with API tests as the connection test failed")
        sys.exit(1)
    
    if not test_simple_scrape():
        print("Simple scrape test failed, cannot proceed with Austender test")
        sys.exit(1)
    
    test_austender_scrape()
