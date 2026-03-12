"""
Configuration management for Job Search Agent.
Loads configuration from environment variables.
"""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for Job Search Agent."""
    
    # Groq API Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  # Updated from decommissioned llama-3.1-70b-versatile
    
    # Gmail SMTP Configuration
    GMAIL_USER: str = os.getenv("GMAIL_USER", "")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
    EMAIL_TO: str = os.getenv("EMAIL_TO", "")
    
    # Job Search Configuration
    JOB_KEYWORDS: List[str] = os.getenv("JOB_KEYWORDS", "").split(",") if os.getenv("JOB_KEYWORDS") else []
    JOB_LOCATION: str = os.getenv("JOB_LOCATION", "Remote")
    MAX_JOBS: int = int(os.getenv("MAX_JOBS", "100"))
    
    # User Profile (for better job matching)
    USER_SKILLS: str = os.getenv("USER_SKILLS", "")  # Comma-separated: "Python, JavaScript, AWS, Docker"
    USER_EXPERIENCE_LEVEL: str = os.getenv("USER_EXPERIENCE_LEVEL", "")  # "Entry", "Mid", "Senior", "Lead"
    USER_YEARS_EXPERIENCE: float = float(os.getenv("USER_YEARS_EXPERIENCE", "0"))  # Years of experience (e.g., 1.5)
    USER_PREFERENCES: str = os.getenv("USER_PREFERENCES", "")  # Any specific preferences or requirements
    USER_INDUSTRY: str = os.getenv("USER_INDUSTRY", "")  # Preferred industry: "Tech", "Finance", etc.
    USER_CURRENT_ROLE: str = os.getenv("USER_CURRENT_ROLE", "")  # Current role (e.g., "SDE-1")
    
    # Web Scraping Configuration
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    REQUEST_DELAY: float = float(os.getenv("REQUEST_DELAY", "2.0"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    
    # LinkedIn Configuration
    LINKEDIN_EMAIL: str = os.getenv("LINKEDIN_EMAIL", "")
    LINKEDIN_PASSWORD: str = os.getenv("LINKEDIN_PASSWORD", "")
    
    # Job Platform Configuration
    INDEED_ENABLED: bool = os.getenv("INDEED_ENABLED", "true").lower() == "true"
    LINKEDIN_ENABLED: bool = os.getenv("LINKEDIN_ENABLED", "true").lower() == "true"
    NAUKRI_ENABLED: bool = os.getenv("NAUKRI_ENABLED", "true").lower() == "true"
    GLASSDOOR_ENABLED: bool = os.getenv("GLASSDOOR_ENABLED", "true").lower() == "true"
    HIRIST_ENABLED: bool = os.getenv("HIRIST_ENABLED", "true").lower() == "true"
    WELLFOUND_ENABLED: bool = os.getenv("WELLFOUND_ENABLED", "true").lower() == "true"
    JOBSLEVER_ENABLED: bool = os.getenv("JOBSLEVER_ENABLED", "true").lower() == "true"
    
    # API-based Job Search (Legal & Reliable)
    JSEARCH_API_KEY: str = os.getenv("JSEARCH_API_KEY", "")  # Free API key from RapidAPI
    JSEARCH_ENABLED: bool = os.getenv("JSEARCH_ENABLED", "true").lower() == "true"  # Recommended!
    JSEARCH_MAX_DAILY_REQUESTS: int = int(os.getenv("JSEARCH_MAX_DAILY_REQUESTS", "6"))  # Max 6/day = 180/month (safe under 200 limit)
    ADZUNA_ENABLED: bool = os.getenv("ADZUNA_ENABLED", "false").lower() == "true"  # Requires API key
    ADZUNA_API_KEY: str = os.getenv("ADZUNA_API_KEY", "")
    ADZUNA_APP_ID: str = os.getenv("ADZUNA_APP_ID", "")

    # Apify Web Scraping (expands job coverage across websites)
    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")
    APIFY_ENABLED: bool = os.getenv("APIFY_ENABLED", "false").lower() == "true"
    
    # AI Filtering Configuration
    AI_FILTER_PROMPT: str = os.getenv(
        "AI_FILTER_PROMPT",
        "Filter jobs that match the user's skills and preferences. Return only job titles that are relevant."
    )
    
    @classmethod
    def validate(cls) -> List[str]:
        """
        Validate that all required configuration is present.
        Returns a list of missing configuration keys.
        """
        missing = []
        
        if not cls.GROQ_API_KEY:
            missing.append("GROQ_API_KEY")
        
        if not cls.GMAIL_USER:
            missing.append("GMAIL_USER")
        
        if not cls.GMAIL_APP_PASSWORD:
            missing.append("GMAIL_APP_PASSWORD")
        
        if not cls.EMAIL_TO:
            missing.append("EMAIL_TO")
        
        if not cls.JOB_KEYWORDS:
            missing.append("JOB_KEYWORDS")
        
        return missing

