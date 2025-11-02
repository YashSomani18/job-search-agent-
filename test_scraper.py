#!/usr/bin/env python3
"""Quick test to see what Naukri/Hirist pages actually return."""
import requests
from bs4 import BeautifulSoup

def test_naukri():
    """Test Naukri scraping."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    session = requests.Session()
    session.get("https://www.naukri.com", headers=headers, timeout=10)
    
    # Try searching for "Java Developer"
    url = "https://www.naukri.com/java-developer-jobs-in-india?k=Java+Developer&l=India"
    response = session.get(url, headers=headers, timeout=10)
    print(f"\n✅ Naukri Response: {response.status_code}")
    print(f"URL: {url}")
    
    soup = BeautifulSoup(response.content, 'html.parser')
    title = soup.find('title')
    if title:
        print(f"Page Title: {title.get_text()[:100]}")
    
    # Check for common Naukri elements
    job_tuples = soup.find_all('div', class_='jobTuple')
    print(f"Found {len(job_tuples)} jobTuple divs")
    
    # Check page content
    body = soup.find('body')
    if body:
        text_preview = body.get_text()[:500].replace('\n', ' ').strip()
        print(f"Body preview: {text_preview}...")

def test_hirist():
    """Test Hirist scraping."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }
    session = requests.Session()
    session.get("https://www.hirist.com/", headers=headers, timeout=10)
    
    url = "https://www.hirist.com/jobs/java-developer-jobs-in-india"
    response = session.get(url, headers=headers, timeout=10)
    print(f"\n✅ Hirist Response: {response.status_code}")
    print(f"URL: {url}")
    
    soup = BeautifulSoup(response.content, 'html.parser')
    title = soup.find('title')
    if title:
        print(f"Page Title: {title.get_text()[:100]}")
    
    job_cards = soup.find_all('div', class_='job-card')
    print(f"Found {len(job_cards)} job-card divs")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Job Site Scrapers")
    print("=" * 60)
    try:
        test_naukri()
    except Exception as e:
        print(f"❌ Naukri test failed: {e}")
    
    try:
        test_hirist()
    except Exception as e:
        print(f"❌ Hirist test failed: {e}")
    
    print("\n" + "=" * 60)
