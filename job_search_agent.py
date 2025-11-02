"""
AI-Powered Job Search Agent
Searches for jobs on LinkedIn and Indeed, filters using Groq API, and sends results via email.
"""
import logging
import time
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from groq import Groq
from config import Config
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('job_search.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class JobSearchAgent:
    """Main agent class for searching and filtering jobs."""
    
    def __init__(self):
        """Initialize the job search agent."""
        self.config = Config
        missing_config = self.config.validate()
        if missing_config:
            raise ValueError(f"Missing required configuration: {', '.join(missing_config)}")
        
        self.groq_client = Groq(api_key=self.config.GROQ_API_KEY)
        self.jsearch_requests_file = ".jsearch_requests.json"  # File to track daily API calls
        self.platform_failures_file = ".platform_failures.json"  # Track platform failures
        self.all_jobs: List[Dict[str, str]] = []
        self.max_consecutive_failures = 5  # Disable platform after 5 consecutive failures
    
    def _track_platform_failure(self, platform_name: str, failed: bool):
        """Track platform failures and auto-disable after consecutive failures."""
        try:
            if os.path.exists(self.platform_failures_file):
                with open(self.platform_failures_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {}
            
            if platform_name not in data:
                data[platform_name] = {'consecutive_failures': 0, 'total_failures': 0, 'last_failure': None}
            
            if failed:
                data[platform_name]['consecutive_failures'] += 1
                data[platform_name]['total_failures'] += 1
                data[platform_name]['last_failure'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                if data[platform_name]['consecutive_failures'] >= self.max_consecutive_failures:
                    logger.warning(
                        f"⚠️  Platform '{platform_name}' has failed {data[platform_name]['consecutive_failures']} "
                        f"consecutive times. Consider disabling it by setting {platform_name.upper()}_ENABLED=false "
                        f"in your .env file to save time."
                    )
            else:
                # Reset consecutive failures on success
                data[platform_name]['consecutive_failures'] = 0
            
            with open(self.platform_failures_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug(f"Error tracking platform failures: {e}")
    
    def _try_fallback_keyword(self, platform_name: str, original_keyword: str, location: str, search_func) -> List[Dict[str, str]]:
        """
        Try a more generic fallback keyword when original search returns 0 jobs.
        This helps find jobs when specific keywords don't match but broader terms might.
        
        Args:
            platform_name: Name of the platform (for logging)
            original_keyword: The original keyword that returned 0 jobs
            location: Job location
            search_func: The search function to call
            
        Returns:
            List of job dictionaries (may be empty)
        """
        # Create fallback keyword mappings - more generic terms
        # These help find jobs when specific keywords don't match
        fallback_map = {
            'java developer': 'software engineer',
            'springboot developer': 'backend developer',
            'springboot': 'java developer',
            'go developer': 'software engineer',
            'react developer': 'frontend developer',
            'sde-1': 'software engineer',
            'sde-2': 'software engineer',
            'sde-ii': 'software engineer',
            'sde - 1': 'software engineer',
            'sde - 2': 'software engineer',
            'sde - ii': 'software engineer',
            'backend developer': 'software engineer',
            'frontend developer': 'software engineer',
            'software developer engineer': 'software engineer',
            'software engineering': 'software engineer',
        }
        
        # Get fallback keyword (default to "Software Engineer" if no mapping)
        original_lower = original_keyword.lower().strip()
        fallback_keyword = fallback_map.get(original_lower, 'Software Engineer')
        
        # Only try fallback if it's different from original
        if fallback_keyword.lower().strip() == original_lower:
            return []
        
        # If original keyword is already very generic, don't retry (to avoid infinite loops)
        if original_lower in ['software engineer', 'software developer', 'developer']:
            if fallback_keyword.lower() in ['software engineer', 'software developer', 'developer']:
                return []
        
        try:
            logger.debug(f"Trying fallback keyword '{fallback_keyword}' on {platform_name}...")
            fallback_jobs = search_func(fallback_keyword, location)
            if fallback_jobs:
                logger.info(f"Found {len(fallback_jobs)} jobs on {platform_name} using fallback keyword '{fallback_keyword}'")
            return fallback_jobs
        except Exception as e:
            logger.debug(f"Fallback keyword search failed on {platform_name}: {e}")
            return []
    
    def _is_platform_auto_disabled(self, platform_name: str) -> bool:
        """Check if platform should be auto-disabled due to consecutive failures."""
        try:
            if os.path.exists(self.platform_failures_file):
                with open(self.platform_failures_file, 'r') as f:
                    data = json.load(f)
                    if platform_name in data:
                        failures = data[platform_name].get('consecutive_failures', 0)
                        if failures >= self.max_consecutive_failures:
                            return True
        except Exception:
            pass
        return False
    
    def _get_platform_status_summary(self) -> Dict[str, Dict]:
        """Get summary of platform status for logging."""
        summary = {}
        try:
            if os.path.exists(self.platform_failures_file):
                with open(self.platform_failures_file, 'r') as f:
                    data = json.load(f)
                    for platform, stats in data.items():
                        if stats.get('consecutive_failures', 0) > 0:
                            summary[platform] = {
                                'consecutive_failures': stats.get('consecutive_failures', 0),
                                'total_failures': stats.get('total_failures', 0),
                                'last_failure': stats.get('last_failure', 'Unknown')
                            }
        except Exception:
            pass
        return summary
    
    def search_indeed(self, keywords: str, location: str = "Remote") -> List[Dict[str, str]]:
        """
        Search for jobs on Indeed using web scraping.
        
        Args:
            keywords: Job search keywords
            location: Job location
            
        Returns:
            List of job dictionaries
        """
        if not self.config.INDEED_ENABLED:
            logger.info("Indeed search is disabled")
            return []
        
        jobs = []
        try:
            # Use session for cookies
            session = requests.Session()
            
            # Indeed search URL - use simpler location format
            url = f"https://www.indeed.com/jobs?q={keywords.replace(' ', '+')}&l={location.replace(' ', '+')}"
            
            # More realistic headers to avoid detection
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
            }
            
            logger.info(f"Searching Indeed for: {keywords} in {location}")
            
            # First request to get cookies
            session.get("https://www.indeed.com", headers=headers, timeout=self.config.REQUEST_TIMEOUT)
            time.sleep(1)
            
            # Then search
            response = session.get(
                url,
                headers=headers,
                timeout=self.config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            
            if response.status_code == 403:
                logger.warning("Indeed blocked the request (403 Forbidden). This is common with anti-scraping measures.")
                self._track_platform_failure("Indeed", failed=True)
                return []
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find job cards
            job_cards = soup.find_all('div', class_='job_seen_beacon')
            
            for card in job_cards[:50]:  # Limit to first 50 results
                try:
                    title_elem = card.find('h2', class_='jobTitle')
                    company_elem = card.find('span', class_='companyName')
                    location_elem = card.find('div', class_='companyLocation')
                    link_elem = title_elem.find('a') if title_elem else None
                    
                    if title_elem and company_elem:
                        job = {
                            'title': title_elem.get_text(strip=True),
                            'company': company_elem.get_text(strip=True),
                            'location': location_elem.get_text(strip=True) if location_elem else location,
                            'url': f"https://www.indeed.com{link_elem.get('href', '')}" if link_elem else '',
                            'source': 'Indeed'
                        }
                        jobs.append(job)
                        logger.debug(f"Found job: {job['title']} at {job['company']}")
                except Exception as e:
                    logger.warning(f"Error parsing Indeed job card: {e}")
                    continue
            
            logger.info(f"Found {len(jobs)} jobs on Indeed")
            
            # Track success - only count actual errors, not "no jobs found"
            self._track_platform_failure("Indeed", failed=False)
            if len(jobs) == 0:
                logger.debug("No jobs found on Indeed for this keyword. Trying fallback keyword...")
                fallback_jobs = self._try_fallback_keyword("Indeed", keywords, location, self.search_indeed)
                jobs.extend(fallback_jobs)
            
            time.sleep(self.config.REQUEST_DELAY)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning("Indeed blocked the request (403 Forbidden). Anti-scraping measures are active.")
                self._track_platform_failure("Indeed", failed=True)
            else:
                logger.error(f"HTTP error searching Indeed: {e}")
                self._track_platform_failure("Indeed", failed=True)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching Indeed: {e}")
            self._track_platform_failure("Indeed", failed=True)
        except Exception as e:
            logger.error(f"Unexpected error in Indeed search: {e}")
            self._track_platform_failure("Indeed", failed=True)
        finally:
            if 'session' in locals():
                session.close()
        
        return jobs
    
    def search_linkedin(self, keywords: str, location: str = "Remote") -> List[Dict[str, str]]:
        """
        Search for jobs on LinkedIn using web scraping.
        
        IMPORTANT NOTES ABOUT LINKEDIN:
        - Without login: LinkedIn has strong anti-scraping measures. Basic scraping may return limited/no results.
        - With login: If LINKEDIN_EMAIL and LINKEDIN_PASSWORD are provided, it uses Selenium for better results.
        - Recommended: Use Indeed for better results without login. LinkedIn requires authentication for reliable scraping.
        
        Args:
            keywords: Job search keywords
            location: Job location
            
        Returns:
            List of job dictionaries
        """
        if not self.config.LINKEDIN_ENABLED:
            logger.info("LinkedIn search is disabled")
            return []
        
        # If credentials provided, use Selenium (better results)
        if self.config.LINKEDIN_EMAIL and self.config.LINKEDIN_PASSWORD:
            return self._search_linkedin_with_selenium(keywords, location)
        
        # Otherwise, try basic scraping (limited success)
        return self._search_linkedin_basic(keywords, location)
    
    def _search_linkedin_with_selenium(self, keywords: str, location: str = "Remote") -> List[Dict[str, str]]:
        """
        Search LinkedIn using Selenium with login (better results).
        Requires: selenium, webdriver (Chrome/Firefox)
        
        SECURITY NOTE:
        - This function is READ-ONLY. It ONLY:
          * Logs in to LinkedIn
          * Navigates to job search page
          * Reads job listings (title, company, location, URL)
          * Closes the browser
        - It does NOT:
          * Post anything
          * Update your profile
          * Like, comment, or share anything
          * Send messages
          * Apply to jobs automatically
          * Modify any data
        - Your credentials are stored securely in .env file (never committed to git)
        
        Args:
            keywords: Job search keywords
            location: Job location
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options
            from selenium.common.exceptions import TimeoutException, NoSuchElementException
            
            logger.info("Using Selenium to search LinkedIn (requires login)...")
            
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument(f'user-agent={self.config.USER_AGENT}')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            try:
                # Login to LinkedIn
                driver.get("https://www.linkedin.com/login")
                time.sleep(2)
                
                email_field = driver.find_element(By.ID, "username")
                password_field = driver.find_element(By.ID, "password")
                
                email_field.send_keys(self.config.LINKEDIN_EMAIL)
                password_field.send_keys(self.config.LINKEDIN_PASSWORD)
                
                login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                login_button.click()
                
                time.sleep(5)  # Wait for login
                
                # Search jobs
                search_url = f"https://www.linkedin.com/jobs/search/?keywords={keywords.replace(' ', '%20')}&location={location.replace(' ', '%20')}"
                driver.get(search_url)
                time.sleep(3)
                
                # Find job listings
                job_cards = driver.find_elements(By.CSS_SELECTOR, "div.base-search-card__info")
                
                for card in job_cards[:50]:  # Limit to first 50
                    try:
                        title = card.find_element(By.CSS_SELECTOR, "h3.base-search-card__title").text
                        company = card.find_element(By.CSS_SELECTOR, "h4.base-search-card__subtitle").text
                        location_elem = card.find_elements(By.CSS_SELECTOR, "span.job-search-card__location")
                        job_location = location_elem[0].text if location_elem else location
                        
                        # Find link
                        parent = card.find_element(By.XPATH, "./ancestor::a[contains(@class, 'base-card__full-link')]")
                        job_url = parent.get_attribute('href')
                        
                        job = {
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'url': job_url,
                            'source': 'LinkedIn'
                        }
                        jobs.append(job)
                        logger.debug(f"Found job: {job['title']} at {job['company']}")
                    except (NoSuchElementException, IndexError) as e:
                        logger.warning(f"Error parsing LinkedIn job card: {e}")
                        continue
                
                logger.info(f"Found {len(jobs)} jobs on LinkedIn (with login)")
                
            finally:
                driver.quit()
            
        except ImportError:
            logger.warning("Selenium not properly installed. Install with: pip install selenium")
            logger.info("Falling back to basic LinkedIn search without login")
            return self._search_linkedin_basic(keywords, location)
        except Exception as e:
            logger.error(f"Error in Selenium LinkedIn search: {e}")
            logger.info("Falling back to basic LinkedIn search without login")
            return self._search_linkedin_basic(keywords, location)
    
    def _search_linkedin_basic(self, keywords: str, location: str = "Remote") -> List[Dict[str, str]]:
        """
        Basic LinkedIn search without login (fallback method).
        
        Args:
            keywords: Job search keywords
            location: Job location
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        try:
            logger.warning("LinkedIn scraping without login may have limited results. LinkedIn blocks most scraping attempts.")
            
            # LinkedIn job search URL
            url = f"https://www.linkedin.com/jobs/search/?keywords={keywords.replace(' ', '%20')}&location={location.replace(' ', '%20')}"
            
            headers = {
                'User-Agent': self.config.USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            logger.info(f"Searching LinkedIn (without login) for: {keywords} in {location}")
            response = requests.get(
                url,
                headers=headers,
                timeout=self.config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # LinkedIn job listings
            job_cards = soup.find_all('div', class_='base-search-card__info')
            
            for card in job_cards[:50]:  # Limit to first 50 results
                try:
                    title_elem = card.find('h3', class_='base-search-card__title')
                    company_elem = card.find('h4', class_='base-search-card__subtitle')
                    location_elem = card.find('span', class_='job-search-card__location')
                    
                    # Find parent link
                    parent_link = card.find_parent('a', class_='base-card__full-link')
                    job_url = parent_link.get('href', '') if parent_link else ''
                    
                    if title_elem and company_elem:
                        job = {
                            'title': title_elem.get_text(strip=True),
                            'company': company_elem.get_text(strip=True),
                            'location': location_elem.get_text(strip=True) if location_elem else location,
                            'url': job_url,
                            'source': 'LinkedIn'
                        }
                        jobs.append(job)
                        logger.debug(f"Found job: {job['title']} at {job['company']}")
                except Exception as e:
                    logger.warning(f"Error parsing LinkedIn job card: {e}")
                    continue
            
            logger.info(f"Found {len(jobs)} jobs on LinkedIn")
            if len(jobs) == 0:
                logger.warning("No jobs found on LinkedIn. This is common without login. Consider using Indeed or providing LinkedIn credentials.")
            time.sleep(self.config.REQUEST_DELAY)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching LinkedIn: {e}")
            logger.info("LinkedIn blocked the request. Try providing LINKEDIN_EMAIL and LINKEDIN_PASSWORD for better results.")
        except Exception as e:
            logger.error(f"Unexpected error in LinkedIn search: {e}")
        
        return jobs
    
    def search_naukri(self, keywords: str, location: str = "India") -> List[Dict[str, str]]:
        """
        Search for jobs on Naukri.com using web scraping.
        Naukri.com is a popular Indian job portal with good coverage of Indian jobs.
        
        Args:
            keywords: Job search keywords
            location: Job location (default: India)
            
        Returns:
            List of job dictionaries
        """
        if not self.config.NAUKRI_ENABLED:
            logger.info("Naukri search is disabled")
            return []
        
        jobs = []
        try:
            # Naukri search URL - try multiple URL formats
            encoded_keywords = keywords.replace(' ', '-').lower()
            encoded_location = location.replace(' ', '-').replace(',', '-').lower()
            
            # Try the standard Naukri search URL format
            url = f"https://www.naukri.com/{encoded_keywords}-jobs-in-{encoded_location}?k={keywords.replace(' ', '+')}&l={location.replace(' ', '+')}"
            
            # More realistic headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Referer': 'https://www.naukri.com/',
            }
            
            # Use session for cookies
            session = requests.Session()
            
            logger.info(f"Searching Naukri for: {keywords} in {location}")
            
            # First request to get cookies
            session.get("https://www.naukri.com", headers=headers, timeout=self.config.REQUEST_TIMEOUT)
            time.sleep(1)
            
            # Then search
            response = session.get(
                url,
                headers=headers,
                timeout=self.config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            
            if response.status_code == 403:
                logger.warning("Naukri blocked the request (403 Forbidden). This is common with anti-scraping measures.")
                return []
            
            response.raise_for_status()
            
            # Parse HTML directly
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Debug: Log page title to verify we got the right page
            page_title = soup.find('title')
            if page_title:
                logger.debug(f"Naukri page title: {page_title.get_text()[:100]}")
            
            # Naukri job listings - try multiple selectors (updated for current structure)
            job_cards = soup.find_all('div', class_='jobTuple')
            if not job_cards:
                job_cards = soup.find_all('article', class_='jobTuple')
            if not job_cards:
                job_cards = soup.find_all('div', class_='srp-jobtuple-wrapper')
            if not job_cards:
                # Try newer Naukri selectors
                job_cards = soup.find_all('div', {'data-testid': 'jobTuple'})
            if not job_cards:
                job_cards = soup.find_all('div', class_='styles_jobListing')
            if not job_cards:
                # Try finding any div with job-related classes
                job_cards = soup.find_all('div', class_=lambda x: x and ('job' in x.lower() or 'listing' in x.lower()))
            
            # Debug: Log how many job cards found
            if job_cards:
                logger.debug(f"Found {len(job_cards)} job cards on Naukri")
            else:
                # Save HTML snippet for debugging
                body_text = soup.find('body')
                if body_text:
                    body_preview = body_text.get_text()[:500].replace('\n', ' ').strip()
                    logger.debug(f"No job cards found on Naukri. Page preview: {body_preview}")
                    # Try to find common Naukri elements
                    common_elements = soup.find_all(['div', 'article'], limit=20)
                    logger.debug(f"Found {len(common_elements)} div/article elements on page")
            
            for card in job_cards[:50]:  # Limit to first 50 results
                try:
                    # Try to find title
                    title_elem = card.find('a', class_='title')
                    if not title_elem:
                        title_elem = card.find('a', {'data-test': 'job-title'})
                    if not title_elem:
                        title_elem = card.find('h2', class_='jobTitle')
                    
                    # Try to find company
                    company_elem = card.find('a', class_='compName')
                    if not company_elem:
                        company_elem = card.find('a', {'data-test': 'company-name'})
                    if not company_elem:
                        company_elem = card.find('span', class_='compName')
                    
                    # Try to find location
                    location_elem = card.find('span', class_='locWdth')
                    if not location_elem:
                        location_elem = card.find('li', class_='location')
                    if not location_elem:
                        location_elem = card.find('div', class_='locality')
                    
                    if title_elem:
                        job = {
                            'title': title_elem.get_text(strip=True),
                            'company': company_elem.get_text(strip=True) if company_elem else 'Not specified',
                            'location': location_elem.get_text(strip=True) if location_elem else location,
                            'url': title_elem.get('href', '') if title_elem.name == 'a' else '',
                            'source': 'Naukri'
                        }
                        
                        # Ensure full URL
                        if job['url'] and not job['url'].startswith('http'):
                            job['url'] = f"https://www.naukri.com{job['url']}"
                        
                        if job['title']:
                            jobs.append(job)
                            logger.debug(f"Found job: {job['title']} at {job['company']}")
                except Exception as e:
                    logger.warning(f"Error parsing Naukri job card: {e}")
                    continue
            
            logger.info(f"Found {len(jobs)} jobs on Naukri")
            # Track success - only count actual errors, not "no jobs found"
            self._track_platform_failure("Naukri", failed=False)
            if len(jobs) == 0:
                logger.debug("No jobs found on Naukri for this keyword. Trying fallback keyword...")
                # Try a more generic fallback keyword if no jobs found
                fallback_jobs = self._try_fallback_keyword("Naukri", keywords, location, self.search_naukri)
                jobs.extend(fallback_jobs)
            time.sleep(self.config.REQUEST_DELAY)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning("Naukri blocked the request (403 Forbidden). Anti-scraping measures are active.")
                self._track_platform_failure("Naukri", failed=True)
            elif e.response.status_code == 400:
                logger.warning("Naukri returned 400 Bad Request. URL format may need adjustment.")
            else:
                logger.error(f"HTTP error searching Naukri: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching Naukri: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Naukri search: {e}")
        finally:
            if 'session' in locals():
                session.close()
        
        return jobs
    
    def search_glassdoor(self, keywords: str, location: str = "India") -> List[Dict[str, str]]:
        """
        Search for jobs on Glassdoor.com using web scraping.
        Glassdoor is a popular job portal with company reviews and salary information.
        
        Args:
            keywords: Job search keywords
            location: Job location (default: India)
            
        Returns:
            List of job dictionaries
        """
        if not self.config.GLASSDOOR_ENABLED:
            logger.info("Glassdoor search is disabled")
            return []
        
        jobs = []
        try:
            # Glassdoor search URL
            encoded_keywords = keywords.replace(' ', '-').replace(',', '')
            encoded_location = location.replace(' ', '-').replace(',', '')
            
            # Glassdoor job search URL
            url = f"https://www.glassdoor.co.in/Job/jobs.htm?sc.keyword={keywords.replace(' ', '+')}&locT=C&locId=1156991"  # India location ID
            
            # More realistic headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Referer': 'https://www.glassdoor.co.in/',
            }
            
            # Use session for cookies
            session = requests.Session()
            
            logger.info(f"Searching Glassdoor for: {keywords} in {location}")
            
            # First request to get cookies
            session.get("https://www.glassdoor.co.in/", headers=headers, timeout=self.config.REQUEST_TIMEOUT)
            time.sleep(1)
            
            # Then search
            response = session.get(
                url,
                headers=headers,
                timeout=self.config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            
            if response.status_code == 403:
                logger.warning("Glassdoor blocked the request (403 Forbidden). This is common with anti-scraping measures.")
                self._track_platform_failure("Glassdoor", failed=True)
                return []
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Glassdoor job listings - try multiple selectors
            job_cards = soup.find_all('li', class_='react-job-listing')
            if not job_cards:
                job_cards = soup.find_all('div', {'data-test': 'jobListing'})
            if not job_cards:
                job_cards = soup.find_all('article', class_='JobCard')
            
            for card in job_cards[:50]:  # Limit to first 50 results
                try:
                    # Try to find title
                    title_elem = card.find('a', {'data-test': 'job-title'})
                    if not title_elem:
                        title_elem = card.find('h2', class_='jobTitle')
                    if not title_elem:
                        title_elem = card.find('a', class_='jobLink')
                    
                    # Try to find company
                    company_elem = card.find('span', {'data-test': 'employer-name'})
                    if not company_elem:
                        company_elem = card.find('div', class_='employerName')
                    if not company_elem:
                        company_elem = card.find('span', class_='employerName')
                    
                    # Try to find location
                    location_elem = card.find('span', {'data-test': 'job-location'})
                    if not location_elem:
                        location_elem = card.find('div', class_='location')
                    if not location_elem:
                        location_elem = card.find('span', class_='jobLocation')
                    
                    # Try to find posted date
                    date_elem = card.find('div', {'data-test': 'job-age'})
                    if not date_elem:
                        date_elem = card.find('span', class_='jobAge')
                    
                    if title_elem:
                        job_url = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        if not job_url.startswith('http'):
                            job_url = f"https://www.glassdoor.co.in{job_url}" if job_url else ''
                        
                        job = {
                            'title': title_elem.get_text(strip=True),
                            'company': company_elem.get_text(strip=True) if company_elem else 'Not specified',
                            'location': location_elem.get_text(strip=True) if location_elem else location,
                            'url': job_url,
                            'source': 'Glassdoor',
                            'date_posted': date_elem.get_text(strip=True) if date_elem else 'Not specified',
                            'scraped_date': datetime.now().strftime('%Y-%m-%d')
                        }
                        
                        if job['title']:
                            jobs.append(job)
                            logger.debug(f"Found job: {job['title']} at {job['company']}")
                except Exception as e:
                    logger.warning(f"Error parsing Glassdoor job card: {e}")
                    continue
            
            logger.info(f"Found {len(jobs)} jobs on Glassdoor")
            # Track success - only count actual errors, not "no jobs found"
            self._track_platform_failure("Glassdoor", failed=False)
            if len(jobs) == 0:
                logger.debug("No jobs found on Glassdoor for this keyword. Trying fallback keyword...")
                fallback_jobs = self._try_fallback_keyword("Glassdoor", keywords, location, self.search_glassdoor)
                jobs.extend(fallback_jobs)
            time.sleep(self.config.REQUEST_DELAY)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning("Glassdoor blocked the request (403 Forbidden). Anti-scraping measures are active.")
            else:
                logger.error(f"HTTP error searching Glassdoor: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching Glassdoor: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Glassdoor search: {e}")
        finally:
            if 'session' in locals():
                session.close()
        
        return jobs
    
    def _get_jsearch_request_count(self) -> int:
        """
        Get today's JSearch API request count.
        
        Returns:
            Number of requests made today
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        try:
            if os.path.exists(self.jsearch_requests_file):
                with open(self.jsearch_requests_file, 'r') as f:
                    data = json.load(f)
                    if data.get('date') == today:
                        return data.get('count', 0)
            return 0
        except Exception as e:
            logger.warning(f"Error reading JSearch request count: {e}")
            return 0
    
    def _increment_jsearch_request_count(self) -> int:
        """
        Increment today's JSearch API request count.
        
        Returns:
            Updated request count for today
        """
        today = datetime.now().strftime('%Y-%m-%d')
        current_count = self._get_jsearch_request_count()
        new_count = current_count + 1
        
        try:
            with open(self.jsearch_requests_file, 'w') as f:
                json.dump({'date': today, 'count': new_count}, f)
            logger.debug(f"JSearch API request count: {new_count}/{self.config.JSEARCH_MAX_DAILY_REQUESTS} today")
            return new_count
        except Exception as e:
            logger.warning(f"Error saving JSearch request count: {e}")
            return new_count
    
    def search_jsearch_api(self, keywords: str, location: str = "India") -> List[Dict[str, str]]:
        """
        Search for jobs using JSearch API (Legal & Reliable).
        JSearch API aggregates jobs from Google Jobs and other public sources.
        FREE TIER AVAILABLE on RapidAPI.
        
        Args:
            keywords: Job search keywords
            location: Job location
            
        Returns:
            List of job dictionaries
        """
        if not self.config.JSEARCH_ENABLED:
            logger.info("JSearch API search is disabled")
            return []
        
        if not self.config.JSEARCH_API_KEY:
            logger.warning("JSearch API key not provided. Get free API key from RapidAPI: https://rapidapi.com/letscrape/api/jsearch")
            return []
        
        # Check daily rate limit (6 requests/day = 180/month, safe under 200 limit)
        current_count = self._get_jsearch_request_count()
        if current_count >= self.config.JSEARCH_MAX_DAILY_REQUESTS:
            logger.warning(
                f"JSearch API daily limit reached: {current_count}/{self.config.JSEARCH_MAX_DAILY_REQUESTS} requests today. "
                f"Skipping to avoid exceeding monthly limit (200 requests/month). "
                f"Limit resets at midnight."
            )
            return []
        
        # Increment request count before making the API call
        new_count = self._increment_jsearch_request_count()
        if new_count > self.config.JSEARCH_MAX_DAILY_REQUESTS:
            logger.warning(f"JSearch API: Request count exceeded limit, skipping this call")
            return []
        
        jobs = []
        try:
            # JSearch API endpoint (via RapidAPI)
            url = "https://jsearch.p.rapidapi.com/search"
            
            # Build query - for India searches, use country code "in"
            # Support both single keyword and combined keywords (with OR)
            if location.lower() == "india" or location.lower() == "remote":
                query = f"{keywords} in India"
                country = "in"  # India country code
            else:
                query = f"{keywords} in {location}"
                country = "us"  # Default to US, can be customized
            
            params = {
                "query": query,
                "page": "1",
                "num_pages": "1",
                "country": country,
                "date_posted": "all"  # Get all jobs (can be: all, today, week, month)
            }
            
            headers = {
                "x-rapidapi-key": self.config.JSEARCH_API_KEY,
                "x-rapidapi-host": "jsearch.p.rapidapi.com"
            }
            
            logger.info(f"Searching JSearch API for: {keywords} in {location}")
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT
            )
            
            if response.status_code == 401:
                logger.error("JSearch API: Invalid API key. Please check your JSEARCH_API_KEY")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            # Parse API response - check structure matches actual API
            if isinstance(data, dict):
                # Check if status is OK
                if data.get('status') != 'OK':
                    logger.warning(f"JSearch API returned status: {data.get('status')}")
                
                # Extract job listings from data array
                if 'data' in data and isinstance(data['data'], list):
                    job_listings = data['data']
                    logger.info(f"JSearch API returned {len(job_listings)} jobs")
                    
                    for job_data in job_listings[:50]:  # Limit to first 50
                        try:
                            # Parse job title
                            job_title = job_data.get('job_title', '').strip()
                            if not job_title:
                                continue
                            
                            # Parse company name
                            employer_name = job_data.get('employer_name', '').strip()
                            if not employer_name:
                                employer_name = 'Unknown'
                            
                            # Parse location - use job_location if available, otherwise construct from city/state/country
                            job_location_raw = job_data.get('job_location', '')
                            if job_location_raw:
                                job_location = job_location_raw
                            else:
                                city = job_data.get('job_city', '')
                                state = job_data.get('job_state', '')
                                country = job_data.get('job_country', '')
                                parts = [p for p in [city, state, country] if p]
                                job_location = ', '.join(parts) if parts else location
                            
                            # Parse URL - prefer apply link, fallback to google link
                            job_url = job_data.get('job_apply_link', '') or job_data.get('job_google_link', '')
                            if not job_url:
                                continue
                            
                            # Parse date - extract date from datetime_utc
                            date_posted = 'Not specified'
                            if job_data.get('job_posted_at_datetime_utc'):
                                try:
                                    date_str = job_data['job_posted_at_datetime_utc']
                                    if 'T' in date_str:
                                        date_posted = date_str.split('T')[0]
                                    else:
                                        date_posted = date_str
                                except Exception:
                                    pass
                            
                            # Check if remote job
                            is_remote = job_data.get('job_is_remote', False)
                            
                            job = {
                                'title': job_title,
                                'company': employer_name,
                                'location': job_location,
                                'url': job_url,
                                'source': 'JSearch API',
                                'date_posted': date_posted,
                                'scraped_date': datetime.now().strftime('%Y-%m-%d'),
                                'job_id': job_data.get('job_id', ''),
                                'is_remote': is_remote,
                                'employment_type': job_data.get('job_employment_type', ''),
                            }
                            
                            # Lenient filtering: Accept all jobs from JSearch API
                            # JSearch API already filters by country="in" (India), so we trust the API's location filter
                            # Many jobs list only city names (e.g., "Bangalore") without "India", but they're still India jobs
                            jobs.append(job)
                            logger.debug(f"Found job: {job_title} at {employer_name} ({job_location})")
                                
                        except Exception as e:
                            logger.warning(f"Error parsing JSearch job: {e}")
                            continue
                else:
                    logger.warning("JSearch API response missing 'data' array")
            else:
                logger.warning("JSearch API response is not a dictionary")
            
            logger.info(f"Found {len(jobs)} jobs from JSearch API")
            time.sleep(self.config.REQUEST_DELAY)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("JSearch API: Invalid API key")
            elif e.response.status_code == 429:
                logger.warning("JSearch API: Rate limit exceeded. Please wait or upgrade plan.")
            else:
                logger.error(f"HTTP error searching JSearch API: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching JSearch API: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in JSearch API search: {e}")
        
        return jobs
    
    def search_adzuna_api(self, keywords: str, location: str = "India") -> List[Dict[str, str]]:
        """
        Search for jobs using Adzuna API (Legal & Reliable).
        Adzuna aggregates jobs from multiple sources.
        Requires API key and App ID from Adzuna (free tier available).
        
        Args:
            keywords: Job search keywords
            location: Job location
            
        Returns:
            List of job dictionaries
        """
        if not self.config.ADZUNA_ENABLED:
            logger.info("Adzuna API search is disabled")
            return []
        
        if not self.config.ADZUNA_API_KEY or not self.config.ADZUNA_APP_ID:
            logger.warning("Adzuna API credentials not provided. Get free API key from: https://developer.adzuna.com/")
            return []
        
        jobs = []
        try:
            # Adzuna API endpoint (India)
            url = "https://api.adzuna.com/v1/api/jobs/in/search/1"
            
            params = {
                "app_id": self.config.ADZUNA_APP_ID,
                "app_key": self.config.ADZUNA_API_KEY,
                "what": keywords,
                "where": location.lower() if location.lower() != "india" else "",
                "results_per_page": 50
            }
            
            logger.info(f"Searching Adzuna API for: {keywords} in {location}")
            response = requests.get(
                url,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT
            )
            
            if response.status_code == 401:
                logger.error("Adzuna API: Invalid credentials")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            # Parse API response
            if isinstance(data, dict) and 'results' in data:
                job_listings = data['results']
                for job_data in job_listings[:50]:
                    try:
                        job = {
                            'title': job_data.get('title', ''),
                            'company': job_data.get('company', {}).get('display_name', 'Unknown'),
                            'location': job_data.get('location', {}).get('display_name', location),
                            'url': job_data.get('redirect_url', ''),
                            'source': 'Adzuna',
                            'date_posted': job_data.get('created', '').split('T')[0] if job_data.get('created') else 'Not specified',
                            'scraped_date': datetime.now().strftime('%Y-%m-%d')
                        }
                        
                        if job['title'] and job['company']:
                            jobs.append(job)
                            logger.debug(f"Found job: {job['title']} at {job['company']}")
                    except Exception as e:
                        logger.warning(f"Error parsing Adzuna job: {e}")
                        continue
            
            logger.info(f"Found {len(jobs)} jobs from Adzuna API")
            time.sleep(self.config.REQUEST_DELAY)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Adzuna API: Invalid API credentials")
            elif e.response.status_code == 429:
                logger.warning("Adzuna API: Rate limit exceeded")
            else:
                logger.error(f"HTTP error searching Adzuna API: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching Adzuna API: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Adzuna API search: {e}")
        
        return jobs
    
    def search_hirist(self, keywords: str, location: str = "India") -> List[Dict[str, str]]:
        """
        Search for jobs on Hirist.com using web scraping.
        Hirist is a popular Indian tech job portal focused on IT and technology roles.
        
        Args:
            keywords: Job search keywords
            location: Job location (default: India)
            
        Returns:
            List of job dictionaries
        """
        if not self.config.HIRIST_ENABLED:
            logger.info("Hirist search is disabled")
            return []
        
        # Auto-disable if too many consecutive failures
        if self._is_platform_auto_disabled("Hirist"):
            logger.debug("Hirist auto-disabled due to consecutive failures")
            return []
        
        jobs = []
        try:
            session = requests.Session()
            
            # Hirist search URL
            url = f"https://www.hirist.com/jobs/{keywords.replace(' ', '-').lower()}-jobs-in-{location.lower().replace(' ', '-')}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Referer': 'https://www.hirist.com/',
            }
            
            logger.info(f"Searching Hirist for: {keywords} in {location}")
            
            session.get("https://www.hirist.com/", headers=headers, timeout=self.config.REQUEST_TIMEOUT)
            time.sleep(1)
            
            response = session.get(
                url,
                headers=headers,
                timeout=self.config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            
            if response.status_code == 403:
                logger.warning("Hirist blocked the request (403 Forbidden). This is common with anti-scraping measures.")
                return []
            
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Debug: Log page title
            page_title = soup.find('title')
            if page_title:
                logger.debug(f"Hirist page title: {page_title.get_text()[:100]}")
            
            # Hirist job listings - try multiple selectors
            job_cards = soup.find_all('div', class_='job-card')
            if not job_cards:
                job_cards = soup.find_all('div', class_='jobListing')
            if not job_cards:
                job_cards = soup.find_all('article', class_='job-card')
            if not job_cards:
                job_cards = soup.find_all('div', class_='job-item')
            if not job_cards:
                # Try finding divs with job-related classes
                job_cards = soup.find_all('div', class_=lambda x: x and 'job' in x.lower())
            
            if job_cards:
                logger.debug(f"Found {len(job_cards)} job cards on Hirist")
            else:
                logger.debug("No job cards found on Hirist - site structure may have changed")
            
            for card in job_cards[:50]:
                try:
                    title_elem = card.find('h3') or card.find('h2') or card.find('a', class_='job-title')
                    company_elem = card.find('span', class_='company') or card.find('div', class_='company-name')
                    location_elem = card.find('span', class_='location') or card.find('div', class_='job-location')
                    link_elem = card.find('a', href=True)
                    
                    title = title_elem.get_text(strip=True) if title_elem else ''
                    company = company_elem.get_text(strip=True) if company_elem else 'Unknown'
                    job_location = location_elem.get_text(strip=True) if location_elem else location
                    
                    if link_elem:
                        job_url = link_elem['href']
                        if not job_url.startswith('http'):
                            job_url = f"https://www.hirist.com{job_url}"
                    else:
                        job_url = f"https://www.hirist.com/jobs/{keywords.replace(' ', '-').lower()}-jobs-in-{location.lower().replace(' ', '-')}"
                    
                    if title and company:
                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'url': job_url,
                            'source': 'Hirist',
                            'date_posted': 'Not specified',
                            'scraped_date': datetime.now().strftime('%Y-%m-%d')
                        })
                        logger.debug(f"Found job: {title} at {company}")
                except Exception as e:
                    logger.warning(f"Error parsing Hirist job: {e}")
                    continue
            
            logger.info(f"Found {len(jobs)} jobs from Hirist")
            # Track success - only count actual errors, not "no jobs found"
            self._track_platform_failure("Hirist", failed=False)
            if len(jobs) == 0:
                logger.debug("No jobs found on Hirist for this keyword. Trying fallback keyword...")
                fallback_jobs = self._try_fallback_keyword("Hirist", keywords, location, self.search_hirist)
                jobs.extend(fallback_jobs)
            time.sleep(self.config.REQUEST_DELAY)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning("Hirist blocked the request (403 Forbidden). Anti-scraping measures are active.")
                self._track_platform_failure("Hirist", failed=True)
            else:
                logger.error(f"HTTP error searching Hirist: {e}")
                self._track_platform_failure("Hirist", failed=True)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching Hirist: {e}")
            self._track_platform_failure("Hirist", failed=True)
        except Exception as e:
            logger.error(f"Unexpected error in Hirist search: {e}")
            self._track_platform_failure("Hirist", failed=True)
        finally:
            if 'session' in locals():
                session.close()
        
        return jobs
    
    def search_wellfound(self, keywords: str, location: str = "India") -> List[Dict[str, str]]:
        """
        Search for jobs on Wellfound (formerly AngelList Talent) using web scraping.
        Wellfound connects startups with job seekers, especially in tech.
        
        Args:
            keywords: Job search keywords
            location: Job location (default: India)
            
        Returns:
            List of job dictionaries
        """
        if not self.config.WELLFOUND_ENABLED:
            logger.info("Wellfound search is disabled")
            return []
        
        jobs = []
        try:
            session = requests.Session()
            
            # Wellfound search URL - try remote first for India
            location_param = "remote" if location.lower() in ["india", "remote"] else location.lower()
            url = f"https://wellfound.com/role/l/software-engineer?search={keywords.replace(' ', '+')}&location={location_param}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Referer': 'https://wellfound.com/',
            }
            
            logger.info(f"Searching Wellfound for: {keywords} in {location}")
            
            session.get("https://wellfound.com/", headers=headers, timeout=self.config.REQUEST_TIMEOUT)
            time.sleep(1)
            
            response = session.get(
                url,
                headers=headers,
                timeout=self.config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            
            if response.status_code == 403:
                logger.warning("Wellfound blocked the request (403 Forbidden). This is common with anti-scraping measures.")
                self._track_platform_failure("Wellfound", failed=True)
                return []
            
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Wellfound job listings - try different selectors
            job_cards = soup.find_all('div', class_='startup')
            if not job_cards:
                job_cards = soup.find_all('div', class_='job-card')
            if not job_cards:
                job_cards = soup.find_all('article', class_='job-listing')
            if not job_cards:
                job_cards = soup.find_all('div', {'data-test': 'job-listing'})
            
            for card in job_cards[:50]:
                try:
                    title_elem = card.find('a', class_='startup-link') or card.find('h3') or card.find('a', href=True)
                    company_elem = card.find('div', class_='startup-name') or card.find('span', class_='company')
                    location_elem = card.find('div', class_='location') or card.find('span', class_='location')
                    link_elem = card.find('a', href=True)
                    
                    title = title_elem.get_text(strip=True) if title_elem else ''
                    company = company_elem.get_text(strip=True) if company_elem else 'Unknown'
                    job_location = location_elem.get_text(strip=True) if location_elem else location
                    
                    if link_elem:
                        job_url = link_elem['href']
                        if not job_url.startswith('http'):
                            job_url = f"https://wellfound.com{job_url}"
                    else:
                        job_url = f"https://wellfound.com/role/l/software-engineer?search={keywords.replace(' ', '+')}"
                    
                    if title and company:
                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'url': job_url,
                            'source': 'Wellfound',
                            'date_posted': 'Not specified',
                            'scraped_date': datetime.now().strftime('%Y-%m-%d')
                        })
                        logger.debug(f"Found job: {title} at {company}")
                except Exception as e:
                    logger.warning(f"Error parsing Wellfound job: {e}")
                    continue
            
            logger.info(f"Found {len(jobs)} jobs from Wellfound")
            # Track success - only count actual errors, not "no jobs found"
            self._track_platform_failure("Wellfound", failed=False)
            if len(jobs) == 0:
                logger.debug("No jobs found on Wellfound for this keyword. Trying fallback keyword...")
                fallback_jobs = self._try_fallback_keyword("Wellfound", keywords, location, self.search_wellfound)
                jobs.extend(fallback_jobs)
            time.sleep(self.config.REQUEST_DELAY)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning("Wellfound blocked the request (403 Forbidden). Anti-scraping measures are active.")
                self._track_platform_failure("Wellfound", failed=True)
            else:
                logger.error(f"HTTP error searching Wellfound: {e}")
                self._track_platform_failure("Wellfound", failed=True)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching Wellfound: {e}")
            self._track_platform_failure("Wellfound", failed=True)
        except Exception as e:
            logger.error(f"Unexpected error in Wellfound search: {e}")
            self._track_platform_failure("Wellfound", failed=True)
        finally:
            if 'session' in locals():
                session.close()
        
        return jobs
    
    def search_jobslever(self, keywords: str, location: str = "India") -> List[Dict[str, str]]:
        """
        Search for jobs on JobsLever using web scraping.
        JobsLever is a job search platform aggregating listings from various sources.
        
        Args:
            keywords: Job search keywords
            location: Job location (default: India)
            
        Returns:
            List of job dictionaries
        """
        if not self.config.JOBSLEVER_ENABLED:
            logger.info("JobsLever search is disabled")
            return []
        
        # Auto-disable if too many consecutive failures
        if self._is_platform_auto_disabled("JobsLever"):
            logger.debug("JobsLever auto-disabled due to consecutive failures")
            return []
        
        jobs = []
        try:
            session = requests.Session()
            
            # JobsLever search URL
            url = f"https://jobslever.com/search?q={keywords.replace(' ', '+')}&location={location.replace(' ', '+')}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Referer': 'https://jobslever.com/',
            }
            
            logger.info(f"Searching JobsLever for: {keywords} in {location}")
            
            session.get("https://jobslever.com/", headers=headers, timeout=self.config.REQUEST_TIMEOUT)
            time.sleep(1)
            
            response = session.get(
                url,
                headers=headers,
                timeout=self.config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            
            if response.status_code == 403:
                logger.warning("JobsLever blocked the request (403 Forbidden). This is common with anti-scraping measures.")
                return []
            
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Debug: Log page title
            page_title = soup.find('title')
            if page_title:
                logger.debug(f"JobsLever page title: {page_title.get_text()[:100]}")
            
            # JobsLever job listings - try multiple selectors
            job_cards = soup.find_all('div', class_='job-card')
            if not job_cards:
                job_cards = soup.find_all('div', class_='job-item')
            if not job_cards:
                job_cards = soup.find_all('article', class_='job-listing')
            if not job_cards:
                job_cards = soup.find_all('div', {'data-testid': 'job-card'})
            if not job_cards:
                # Try finding any elements with job-related classes
                job_cards = soup.find_all('div', class_=lambda x: x and 'job' in x.lower())
            
            if job_cards:
                logger.debug(f"Found {len(job_cards)} job cards on JobsLever")
            else:
                logger.debug("No job cards found on JobsLever - site structure may have changed")
            
            for card in job_cards[:50]:
                try:
                    title_elem = card.find('h2') or card.find('h3') or card.find('a', class_='job-title')
                    company_elem = card.find('span', class_='company') or card.find('div', class_='company-name')
                    location_elem = card.find('span', class_='location') or card.find('div', class_='job-location')
                    link_elem = card.find('a', href=True)
                    
                    title = title_elem.get_text(strip=True) if title_elem else ''
                    company = company_elem.get_text(strip=True) if company_elem else 'Unknown'
                    job_location = location_elem.get_text(strip=True) if location_elem else location
                    
                    if link_elem:
                        job_url = link_elem['href']
                        if not job_url.startswith('http'):
                            job_url = f"https://jobslever.com{job_url}"
                    else:
                        job_url = f"https://jobslever.com/search?q={keywords.replace(' ', '+')}"
                    
                    if title and company:
                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'url': job_url,
                            'source': 'JobsLever',
                            'date_posted': 'Not specified',
                            'scraped_date': datetime.now().strftime('%Y-%m-%d')
                        })
                        logger.debug(f"Found job: {title} at {company}")
                except Exception as e:
                    logger.warning(f"Error parsing JobsLever job: {e}")
                    continue
            
            logger.info(f"Found {len(jobs)} jobs from JobsLever")
            # Track success - only count actual errors, not "no jobs found"
            self._track_platform_failure("JobsLever", failed=False)
            if len(jobs) == 0:
                logger.debug("No jobs found on JobsLever for this keyword. Trying fallback keyword...")
                fallback_jobs = self._try_fallback_keyword("JobsLever", keywords, location, self.search_jobslever)
                jobs.extend(fallback_jobs)
            time.sleep(self.config.REQUEST_DELAY)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning("JobsLever blocked the request (403 Forbidden). Anti-scraping measures are active.")
                self._track_platform_failure("JobsLever", failed=True)
            else:
                logger.error(f"HTTP error searching JobsLever: {e}")
                self._track_platform_failure("JobsLever", failed=True)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching JobsLever: {e}")
            self._track_platform_failure("JobsLever", failed=True)
        except Exception as e:
            logger.error(f"Unexpected error in JobsLever search: {e}")
            self._track_platform_failure("JobsLever", failed=True)
        finally:
            if 'session' in locals():
                session.close()
        
        return jobs
    
    def filter_jobs_by_location(self, jobs: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Filter jobs to include India-based or Remote positions.
        Made lenient to include jobs even if country is not explicitly mentioned.
        Many job listings mention only city names (e.g., "Bangalore", "Hyderabad") without "India".
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            Filtered list with India-based or Remote jobs (lenient filtering)
        """
        filtered = []
        
        # Expanded list of Indian cities/regions (more comprehensive)
        india_cities = [
            'india', 'indian', 'in ',  # Country indicators
            'delhi', 'new delhi', 'ncr', 'gurgaon', 'gurugram', 'noida', 'faridabad', 'ghaziabad',  # NCR region
            'mumbai', 'bangalore', 'bengaluru', 'hyderabad', 'chennai', 'madras',  # Major metros
            'pune', 'kolkata', 'calcutta', 'ahmedabad', 'jaipur',  # Other major cities
            'indore', 'lucknow', 'chandigarh', 'kochi', 'coimbatore',  # Tier 2 cities
            'mysore', 'mangalore', 'trivandrum', 'thiruvananthapuram', 'vadodara', 'baroda',
            'surat', 'nagpur', 'bhopal', 'visakhapatnam', 'vizag', 'patna', 'ludhiana',
            'agra', 'varanasi', 'srinagar', 'amritsar', 'raipur', 'bhubaneswar',
            'rajkot', 'gwalior', 'bhiwandi', 'thanjavur', 'tirupur', 'nashik'
        ]
        
        # Keywords that indicate non-India locations (exclude these)
        non_india_keywords = [
            'usa', 'united states', 'us ', 'uk ', 'united kingdom', 'london', 'canada', 'toronto',
            'vancouver', 'australia', 'sydney', 'melbourne', 'singapore', 'dubai', 'uae',
            'germany', 'france', 'spain', 'italy', 'netherlands', 'sweden', 'norway',
            'new york', 'san francisco', 'los angeles', 'chicago', 'seattle', 'boston',
            'austin', 'denver', 'phoenix', 'philadelphia', 'houston', 'dallas'
        ]
        
        for job in jobs:
            location_lower = job.get('location', '').lower()
            
            # Skip if location explicitly indicates non-India
            if any(non_india_keyword in location_lower for non_india_keyword in non_india_keywords):
                # Exception: If it also mentions India, keep it (e.g., "India and US")
                if 'india' not in location_lower:
                    logger.debug(f"Excluding job (non-India location): {job['title']} - {job['location']}")
                    continue
            
            # Accept if Remote
            if 'remote' in location_lower or 'work from home' in location_lower or 'wfh' in location_lower:
                filtered.append(job)
                continue
            
            # Accept if mentions India or Indian cities (lenient - matches any city)
            is_india = any(city in location_lower for city in india_cities)
            if is_india:
                filtered.append(job)
                continue
            
            # If location is empty or unclear, include it (lenient approach)
            # Many APIs don't include country, just city names
            if not location_lower or location_lower.strip() == '':
                filtered.append(job)  # Include if no location info (assume it's from API's country filter)
                continue
            
            # Last resort: If it doesn't match non-India keywords, include it (very lenient)
            # Better to include a few non-India jobs than exclude India jobs
            logger.debug(f"Including job (lenient filter): {job['title']} - {job['location']}")
            filtered.append(job)
        
        logger.info(f"Location filtering (lenient): {len(jobs)} jobs -> {len(filtered)} jobs")
        return filtered
    
    def filter_jobs_with_ai(self, jobs: List[Dict[str, str]], keywords: str) -> List[Dict[str, str]]:
        """
        Filter jobs using Groq API to find the most relevant matches.
        Uses user profile (skills, experience level, preferences) for better matching.
        
        Args:
            jobs: List of job dictionaries
            keywords: Search keywords for context
            
        Returns:
            Filtered list of job dictionaries
        """
        if not jobs:
            logger.info("No jobs to filter")
            return []
        
        try:
            logger.info(f"Filtering {len(jobs)} jobs using AI with user profile...")
            
            # Prepare job list for AI
            job_list = "\n".join([
                f"- {job['title']} at {job['company']} ({job['location']})"
                for job in jobs[:200]  # Limit for API
            ])
            
            # Build user profile context
            user_profile = f"Search Keywords: {keywords}"
            if self.config.USER_SKILLS:
                user_profile += f"\nUser Skills: {self.config.USER_SKILLS}"
            if self.config.USER_EXPERIENCE_LEVEL:
                user_profile += f"\nExperience Level: {self.config.USER_EXPERIENCE_LEVEL}"
            if self.config.USER_YEARS_EXPERIENCE:
                user_profile += f"\nYears of Experience: {self.config.USER_YEARS_EXPERIENCE}"
            if self.config.USER_CURRENT_ROLE:
                user_profile += f"\nCurrent Role: {self.config.USER_CURRENT_ROLE}"
            if self.config.USER_INDUSTRY:
                user_profile += f"\nPreferred Industry: {self.config.USER_INDUSTRY}"
            if self.config.USER_PREFERENCES:
                user_profile += f"\nPreferences: {self.config.USER_PREFERENCES}"
            
            # Location filtering instruction
            location_note = "\nCRITICAL: Filter jobs by location - Only include jobs that are:"
            location_note += "\n- Remote jobs (can be from anywhere)"
            location_note += "\n- Jobs located in India (any city in India)"
            location_note += "\nEXCLUDE: Jobs with office locations outside India (unless Remote)"
            
            prompt = f"""You are a job matching assistant. Given the following job listings and the user's profile:

{user_profile}
{location_note}

Filter and rank the top {self.config.MAX_JOBS} most relevant jobs that match the user's profile.

Consider:
1. Job title relevance to keywords and skills (focus on Java SpringBoot, Go, React, or Software Engineering)
2. Role level matching user's experience level (SDE-1, 1+ years experience preferred)
3. Industry alignment (Software Engineering, Backend Development)
4. Skills mentioned in job title matching user's skills
5. User preferences and requirements (Pan India only, Remote OK, WFO must be in India)
6. Location filtering: Only India-based or Remote jobs

Job Listings:
{job_list}

Return only the job titles that are most relevant, one per line. Format: "Job Title - Company Name"
If a job is not relevant OR location is outside India (and not Remote), exclude it."""

            response = self.groq_client.chat.completions.create(
                model=self.config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": self.config.AI_FILTER_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            ai_response = response.choices[0].message.content.strip()
            logger.info(f"AI filtering completed")
            
            # Parse AI response and match with original jobs
            filtered_jobs = []
            ai_selected_titles = [line.strip() for line in ai_response.split('\n') if line.strip() and '-' in line]
            
            for ai_line in ai_selected_titles[:self.config.MAX_JOBS]:
                # Try to match AI suggestion with original jobs
                for job in jobs:
                    if job['title'].lower() in ai_line.lower() or ai_line.lower() in job['title'].lower():
                        if job not in filtered_jobs:
                            filtered_jobs.append(job)
                            break
            
            # If AI filtering didn't match well, take top jobs by default
            if len(filtered_jobs) < min(10, len(jobs)):
                logger.warning("AI filtering didn't match well, using top jobs")
                filtered_jobs = jobs[:self.config.MAX_JOBS]
            
            logger.info(f"AI filtered to {len(filtered_jobs)} jobs")
            return filtered_jobs[:self.config.MAX_JOBS]
            
        except Exception as e:
            logger.error(f"Error in AI filtering: {e}")
            logger.info("Falling back to first N jobs without AI filtering")
            return jobs[:self.config.MAX_JOBS]
    
    def create_excel_file(self, jobs: List[Dict[str, str]], filename: str) -> str:
        """
        Create an Excel file with job listings.
        
        Args:
            jobs: List of job dictionaries
            filename: Output filename
            
        Returns:
            Path to created Excel file
        """
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Job Listings"
            
            # Header row
            headers = ['Job ID', 'Job Title', 'Company Name', 'Location', 'Source', 'Date Posted', 'Scraped Date', 'Job URL']
            ws.append(headers)
            
            # Style header row
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF")
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Add job data
            for i, job in enumerate(jobs, 1):
                job_id = job.get('id', f"JOB-{i:03d}")
                row = [
                    job_id,
                    job.get('title', ''),
                    job.get('company', ''),
                    job.get('location', ''),
                    job.get('source', ''),
                    job.get('date_posted', 'Not specified'),
                    job.get('scraped_date', datetime.now().strftime('%Y-%m-%d')),
                    job.get('url', '')
                ]
                ws.append(row)
                
                # Make URL column hyperlink
                url_cell = ws.cell(row=i+1, column=8)
                if job.get('url'):
                    url_cell.hyperlink = job['url']
                    url_cell.style = "Hyperlink"
            
            # Auto-adjust column widths
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
            
            # Freeze header row
            ws.freeze_panes = 'A2'
            
            wb.save(filename)
            logger.info(f"Excel file created: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error creating Excel file: {e}")
            return None
    
    def create_pdf_file(self, jobs: List[Dict[str, str]], filename: str) -> str:
        """
        Create a PDF file with job listings.
        
        Args:
            jobs: List of job dictionaries
            filename: Output filename
            
        Returns:
            Path to created PDF file
        """
        try:
            doc = SimpleDocTemplate(filename, pagesize=A4)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title = Paragraph(f"Job Search Results - {len(jobs)} Jobs Found", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Summary
            summary_text = f"""
            <b>Search Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
            <b>Keywords:</b> {', '.join(self.config.JOB_KEYWORDS)}<br/>
            <b>Location:</b> {self.config.JOB_LOCATION}<br/>
            """
            summary = Paragraph(summary_text, styles['Normal'])
            story.append(summary)
            story.append(Spacer(1, 12))
            
            # Table data
            data = [['Job ID', 'Job Title', 'Company', 'Location', 'Source', 'Date Posted', 'URL']]
            
            for i, job in enumerate(jobs, 1):
                job_id = job.get('id', f"JOB-{i:03d}")
                row = [
                    job_id,
                    job.get('title', '')[:40] + '...' if len(job.get('title', '')) > 40 else job.get('title', ''),
                    job.get('company', '')[:30] + '...' if len(job.get('company', '')) > 30 else job.get('company', ''),
                    job.get('location', '')[:20] + '...' if len(job.get('location', '')) > 20 else job.get('location', ''),
                    job.get('source', ''),
                    job.get('date_posted', 'N/A')[:15],
                    'Link' if job.get('url') else 'N/A'
                ]
                data.append(row)
            
            # Create table
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            story.append(table)
            
            doc.build(story)
            logger.info(f"PDF file created: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error creating PDF file: {e}")
            return None
    
    def send_email(self, jobs: List[Dict[str, str]]) -> bool:
        """
        Send job listings via Gmail SMTP.
        
        Args:
            jobs: List of job dictionaries to send
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not jobs:
            logger.warning("No jobs to send via email")
            return False
        
        try:
            # Create email
            msg = MIMEMultipart()
            msg['From'] = self.config.GMAIL_USER
            msg['To'] = self.config.EMAIL_TO
            msg['Subject'] = f"Job Search Results - {len(jobs)} Jobs Found ({datetime.now().strftime('%Y-%m-%d')})"
            
            # Create email body
            body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .job {{ margin-bottom: 20px; padding: 15px; border-left: 3px solid #0073b1; background-color: #f9f9f9; }}
                    .title {{ font-size: 18px; font-weight: bold; color: #333; }}
                    .company {{ color: #666; margin-top: 5px; }}
                    .location {{ color: #888; font-size: 14px; }}
                    .link {{ margin-top: 10px; }}
                    a {{ color: #0073b1; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                    .header {{ background-color: #0073b1; color: white; padding: 20px; text-align: center; }}
                    .stats {{ padding: 15px; background-color: #e8f4f8; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🎯 Job Search Results</h1>
                    <p>Found {len(jobs)} matching jobs</p>
                </div>
                <div class="stats">
                    <strong>Search Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                    <strong>Keywords:</strong> {', '.join(self.config.JOB_KEYWORDS)}<br>
                    <strong>Location:</strong> {self.config.JOB_LOCATION}
                </div>
            """
            
            for i, job in enumerate(jobs, 1):
                job_id = job.get('id', f"JOB-{i:03d}")  # Generate job ID if not present
                body += f"""
                <div class="job">
                    <div style="font-weight: bold; color: #666; font-size: 12px; margin-bottom: 5px;">Job ID: {job_id}</div>
                    <div class="title">{i}. {job['title']}</div>
                    <div class="company">🏢 <strong>Company:</strong> {job['company']}</div>
                    <div class="location">📍 <strong>Location:</strong> {job['location']}</div>
                    <div class="location">📌 <strong>Source:</strong> {job['source']}</div>
                    <div class="link" style="margin-top: 15px;">
                        <a href="{job['url']}" target="_blank" style="background-color: #0073b1; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Apply Now →</a>
                    </div>
                </div>
                """
            
            body += """
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Ensure all jobs have scraped_date
            for job in jobs:
                if 'scraped_date' not in job:
                    job['scraped_date'] = datetime.now().strftime('%Y-%m-%d')
                if 'date_posted' not in job:
                    job['date_posted'] = 'Not specified'
            
            # Create Excel file
            excel_filename = f"job_listings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            excel_path = self.create_excel_file(jobs, excel_filename)
            
            if excel_path and os.path.exists(excel_path):
                with open(excel_path, 'rb') as f:
                    excel_attachment = MIMEBase('application', 'octet-stream')
                    excel_attachment.set_payload(f.read())
                    encoders.encode_base64(excel_attachment)
                    excel_attachment.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {excel_filename}'
                    )
                    msg.attach(excel_attachment)
            
            # Create PDF file
            pdf_filename = f"job_listings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = self.create_pdf_file(jobs, pdf_filename)
            
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    pdf_attachment = MIMEBase('application', 'octet-stream')
                    pdf_attachment.set_payload(f.read())
                    encoders.encode_base64(pdf_attachment)
                    pdf_attachment.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {pdf_filename}'
                    )
                    msg.attach(pdf_attachment)
            
            # Send email
            logger.info(f"Sending email to {self.config.EMAIL_TO} with Excel and PDF attachments...")
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.config.GMAIL_USER, self.config.GMAIL_APP_PASSWORD)
                server.send_message(msg)
            
            # Clean up temporary files
            if excel_path and os.path.exists(excel_path):
                try:
                    os.remove(excel_path)
                except:
                    pass
            if pdf_path and os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                except:
                    pass
            
            logger.info("Email sent successfully with Excel and PDF attachments!")
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def run(self):
        """Main execution method."""
        logger.info("=" * 50)
        logger.info("Starting Job Search Agent")
        logger.info("=" * 50)
        
        try:
            # Search for jobs
            all_jobs = []
            
            # Optimize JSearch API: Combine all keywords into one API call
            # This uses only 1 request instead of N requests (N = number of keywords)
            if self.config.JSEARCH_ENABLED and self.config.JOB_KEYWORDS:
                # Combine all keywords with OR logic: "Java Developer OR SpringBoot Developer OR ..."
                valid_keywords = [k.strip() for k in self.config.JOB_KEYWORDS if k.strip()]
                if valid_keywords:
                    combined_keywords = " OR ".join(valid_keywords)
                    logger.info(f"Searching JSearch API with combined keywords: {len(valid_keywords)} keywords in one request")
                    jsearch_jobs = self.search_jsearch_api(combined_keywords, self.config.JOB_LOCATION)
                    all_jobs.extend(jsearch_jobs)
            
            # Optimize: Run platform searches in parallel for each keyword
            # This significantly speeds up the search process (8x faster for 8 platforms)
            def search_all_platforms(keyword: str, location: str) -> List[Dict[str, str]]:
                """Search all enabled platforms for a single keyword in parallel."""
                keyword = keyword.strip()
                if not keyword:
                    return []
                
                logger.info(f"Searching for: {keyword}")
                jobs_for_keyword = []
                
                # List of all search functions to run in parallel
                search_functions = []
                
                if self.config.ADZUNA_ENABLED:
                    search_functions.append(('Adzuna', self.search_adzuna_api))
                if self.config.INDEED_ENABLED:
                    search_functions.append(('Indeed', self.search_indeed))
                if self.config.LINKEDIN_ENABLED:
                    search_functions.append(('LinkedIn', self.search_linkedin))
                if self.config.NAUKRI_ENABLED:
                    search_functions.append(('Naukri', self.search_naukri))
                if self.config.GLASSDOOR_ENABLED:
                    search_functions.append(('Glassdoor', self.search_glassdoor))
                if self.config.HIRIST_ENABLED:
                    search_functions.append(('Hirist', self.search_hirist))
                if self.config.WELLFOUND_ENABLED:
                    search_functions.append(('Wellfound', self.search_wellfound))
                if self.config.JOBSLEVER_ENABLED:
                    search_functions.append(('JobsLever', self.search_jobslever))
                
                # Execute searches in parallel (max 8 workers for 8 platforms)
                if search_functions:
                    with ThreadPoolExecutor(max_workers=min(len(search_functions), 8)) as executor:
                        # Submit all search tasks
                        future_to_platform = {
                            executor.submit(search_func, keyword, location): platform_name
                            for platform_name, search_func in search_functions
                        }
                        
                        # Collect results as they complete
                        for future in as_completed(future_to_platform):
                            platform_name = future_to_platform[future]
                            try:
                                platform_jobs = future.result()
                                jobs_for_keyword.extend(platform_jobs)
                                logger.debug(f"{platform_name} returned {len(platform_jobs)} jobs for '{keyword}'")
                            except Exception as e:
                                logger.warning(f"{platform_name} search failed for '{keyword}': {e}")
                
                return jobs_for_keyword
            
            # Process all keywords sequentially (to respect rate limits)
            valid_keywords = [k.strip() for k in self.config.JOB_KEYWORDS if k.strip()]
            
            if valid_keywords:
                logger.info(f"Searching {len(valid_keywords)} keywords across all platforms in parallel...")
                
                for keyword in valid_keywords:
                    keyword_jobs = search_all_platforms(keyword, self.config.JOB_LOCATION)
                    all_jobs.extend(keyword_jobs)
                    # Small delay between keywords to avoid overwhelming servers
                    if keyword != valid_keywords[-1]:  # No delay after last keyword
                        time.sleep(0.5)  # Reduced delay (0.5s instead of 2s) - platforms run in parallel
            
            # Ensure all jobs have date fields - optimized (compute once, reuse)
            scraped_date = datetime.now().strftime('%Y-%m-%d')
            default_date_posted = 'Not specified'
            for job in all_jobs:
                job.setdefault('scraped_date', scraped_date)
                job.setdefault('date_posted', default_date_posted)
            
            # Remove duplicates - optimized with better duplicate detection
            seen = set()
            unique_jobs = []
            for job in all_jobs:
                # Use title, company, and URL for better duplicate detection
                job_key = (
                    job.get('title', '').lower().strip(),
                    job.get('company', '').lower().strip(),
                    job.get('url', '').lower().strip()[:50] if job.get('url') else ''  # First 50 chars of URL
                )
                if job_key not in seen:
                    seen.add(job_key)
                    unique_jobs.append(job)
            
            logger.info(f"Found {len(unique_jobs)} unique jobs total")
            
            # Show platform status summary
            platform_status = self._get_platform_status_summary()
            if platform_status:
                logger.info("=" * 50)
                logger.info("Platform Status Summary:")
                logger.info("=" * 50)
                for platform, stats in sorted(platform_status.items()):
                    logger.info(
                        f"{platform}: {stats['consecutive_failures']} consecutive failures "
                        f"({stats['total_failures']} total) - Last failure: {stats['last_failure']}"
                    )
                    if stats['consecutive_failures'] >= self.max_consecutive_failures:
                        env_key = platform.upper().replace(' ', '_') + "_ENABLED"
                        logger.warning(
                            f"⚠️  Recommendation: Disable {platform} by setting "
                            f"{env_key}=false in .env to save time"
                        )
                logger.info("=" * 50)
                logger.info("Run: python3 check_platform_status.py for detailed analysis")
                logger.info("=" * 50)
            
            # Filter by location first (India-only)
            india_jobs = self.filter_jobs_by_location(unique_jobs)
            
            # Filter with AI
            keywords_str = ', '.join(self.config.JOB_KEYWORDS)
            filtered_jobs = self.filter_jobs_with_ai(india_jobs, keywords_str)
            
            # Send email
            if filtered_jobs:
                self.send_email(filtered_jobs)
                logger.info(f"Successfully processed and sent {len(filtered_jobs)} jobs")
            else:
                logger.warning("No jobs to send after filtering")
            
            logger.info("Job Search Agent completed successfully")
            
        except Exception as e:
            logger.error(f"Fatal error in Job Search Agent: {e}", exc_info=True)
            raise


def main():
    """Main entry point."""
    try:
        agent = JobSearchAgent()
        agent.run()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your .env file and ensure all required variables are set")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)


if __name__ == "__main__":
    main()

