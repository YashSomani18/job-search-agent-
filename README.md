# AI-Powered Job Search Agent

An intelligent job search agent that automatically searches for jobs on LinkedIn, Indeed, and Naukri.com, filters them using AI (Groq API), and sends the top matches via email.

## Features

- 🔍 **Multi-platform Search**: 
  - **API-based (Legal & Reliable)**: JSearch API (aggregates Google Jobs), Adzuna API
  - **Scraping-based**: Indeed, Naukri.com, Glassdoor, LinkedIn, Hirist, Wellfound (AngelList), JobsLever
- 🤖 **AI-Powered Filtering**: Uses Groq API (free tier) to filter and rank jobs
- 📧 **Email Notifications**: Sends top 100 matching jobs via Gmail SMTP with Excel & PDF attachments
- ⏰ **Automated Daily Runs**: GitHub Actions workflow runs daily at 8 AM IST
- 🛡️ **Production Ready**: Comprehensive error handling and logging
- 💰 **100% Free**: Uses free APIs and services
- 🇮🇳 **India-Focused**: Naukri.com integration and API support for excellent Indian job coverage
- ✅ **Legal & Compliant**: Uses official APIs when available, reducing risk of blocks

## Prerequisites

- Python 3.10 or higher
- Gmail account with App Password enabled
- Groq API key (free tier available)
- GitHub account (for automated runs)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd "Job Agent AI"
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Get API Keys and Credentials

#### JSearch API Key (Recommended - Free!)

1. Visit [JSearch API on RapidAPI](https://rapidapi.com/letscrape/api/jsearch)
2. Sign up for a free RapidAPI account
3. Subscribe to the JSearch API (free tier available)
4. Copy your RapidAPI key from the dashboard
5. Use this as your `JSEARCH_API_KEY`

**Note**: JSearch API aggregates jobs from Google Jobs and other public sources, providing reliable, legal access without scraping.

#### Groq API Key

1. Visit [Groq Console](https://console.groq.com/)
2. Sign up for a free account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the API key

#### Gmail App Password

1. Go to your [Google Account](https://myaccount.google.com/)
2. Navigate to **Security** → **2-Step Verification** (enable if not already)
3. Scroll down to **App passwords**
4. Select **Mail** and **Other (Custom name)**
5. Enter "Job Search Agent" as the name
6. Click **Generate**
7. Copy the 16-character password (without spaces)

### 5. Configure Environment Variables

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` file with your credentials:
```bash
# Groq API
GROQ_API_KEY=your_groq_api_key_here

# Gmail SMTP
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_character_app_password
EMAIL_TO=recipient@gmail.com

# Job Search
JOB_KEYWORDS=Python Developer,Software Engineer,Data Scientist
JOB_LOCATION=Remote
MAX_JOBS=100
```

## Usage

### Run Locally

```bash
python job_search_agent.py
```

The script will:
1. Search for jobs on Indeed and LinkedIn
2. Filter jobs using Groq AI
3. Send top matching jobs via email

### Run with GitHub Actions (Automated)

1. Push your code to GitHub
2. Add secrets to GitHub repository:
   - Go to **Settings** → **Secrets and variables** → **Actions**
   - Add the following secrets:
     - `GROQ_API_KEY`: Your Groq API key
     - `GMAIL_USER`: Your Gmail address
     - `GMAIL_APP_PASSWORD`: Your Gmail app password
     - `EMAIL_TO`: Recipient email address
     - `JOB_KEYWORDS`: Comma-separated job keywords (e.g., "Python Developer,Software Engineer")
     - `JOB_LOCATION`: Job location (e.g., "Remote")
     - `USER_SKILLS`: Your skills (optional, but recommended)
     - `USER_EXPERIENCE_LEVEL`: Experience level (optional)
     - `MAX_JOBS`: Maximum jobs to send (default: 100)

3. The workflow will run daily at 8 AM IST (2:30 UTC)

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | Groq API key for AI filtering | Yes |
| `GMAIL_USER` | Gmail address for SMTP | Yes |
| `GMAIL_APP_PASSWORD` | Gmail app password | Yes |
| `EMAIL_TO` | Recipient email address | Yes |
| `JOB_KEYWORDS` | Comma-separated job keywords | Yes |
| `JOB_LOCATION` | Job location | Yes |
| `USER_SKILLS` | Your skills (comma-separated) | No (recommended) |
| `USER_EXPERIENCE_LEVEL` | Experience level: Entry/Mid/Senior/Lead | No (recommended) |
| `USER_INDUSTRY` | Preferred industry | No |
| `USER_PREFERENCES` | Job preferences (e.g., "Remote only") | No |
| `MAX_JOBS` | Maximum jobs to send | No (default: 100) |
| `GROQ_MODEL` | Groq model name | No (default: llama-3.1-70b-versatile) |
| `LINKEDIN_ENABLED` | Enable LinkedIn search | No (default: true) |
| `LINKEDIN_EMAIL` | LinkedIn email (for better results) | No |
| `LINKEDIN_PASSWORD` | LinkedIn password (for better results) | No |
| `INDEED_ENABLED` | Enable Indeed search | No (default: true) |
| `NAUKRI_ENABLED` | Enable Naukri.com search | No (default: true) |
| `GLASSDOOR_ENABLED` | Enable Glassdoor.com search | No (default: true) |
| `HIRIST_ENABLED` | Enable Hirist.com search | No (default: true) |
| `WELLFOUND_ENABLED` | Enable Wellfound (AngelList) search | No (default: true) |
| `JOBSLEVER_ENABLED` | Enable JobsLever search | No (default: true) |
| `JSEARCH_ENABLED` | Enable JSearch API (recommended) | No (default: true) |
| `JSEARCH_API_KEY` | JSearch API key from RapidAPI | No (recommended) |
| `ADZUNA_ENABLED` | Enable Adzuna API | No (default: false) |
| `ADZUNA_API_KEY` | Adzuna API key | No |
| `ADZUNA_APP_ID` | Adzuna App ID | No |
| `REQUEST_DELAY` | Delay between requests (seconds) | No (default: 2.0) |
| `REQUEST_TIMEOUT` | Request timeout (seconds) | No (default: 30) |

### How Does the Agent Know What Jobs You're Looking For?

The agent uses your **user profile** to filter jobs intelligently:

1. **Job Keywords** (`JOB_KEYWORDS`): Basic search terms (e.g., "Python Developer", "Software Engineer")
2. **Your Skills** (`USER_SKILLS`): Comma-separated list of your skills - helps AI match relevant jobs
3. **Experience Level** (`USER_EXPERIENCE_LEVEL`): Entry/Mid/Senior/Lead - filters jobs by seniority
4. **Industry** (`USER_INDUSTRY`): Preferred industry (e.g., "Tech", "Finance")
5. **Preferences** (`USER_PREFERENCES`): Specific requirements (e.g., "Remote only", "Full-time")

The AI uses all this information to filter and rank jobs, so you get the most relevant matches!

**Example `.env` configuration (Personalized):**
```bash
JOB_KEYWORDS=Java Developer,SpringBoot Developer,Go Developer,React Developer,Software Engineer,SDE-1
USER_SKILLS=Java, SpringBoot, Kafka, AWS S3, Docker, PostgreSQL, MySQL, Redis, MongoDB, React.js, Node.js
USER_EXPERIENCE_LEVEL=Mid
USER_YEARS_EXPERIENCE=1.5
USER_CURRENT_ROLE=SDE-1
USER_INDUSTRY=Tech,Software Engineering,Backend Development
USER_PREFERENCES=Pan India only, Remote jobs fine, WFO must be in India, 1+ years experience
JOB_LOCATION=India
```

### LinkedIn Login: Do You Need It?

**Short Answer: No, but it helps!**

- **Without Login**: Basic scraping works for Indeed, but LinkedIn blocks most scraping attempts. You may get limited or no results from LinkedIn.
- **With Login** (optional): If you provide `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD`, the agent uses Selenium to login and search, which gives much better results.
- **Recommendation**: 
  - For **Indeed**: No login needed - works great without it!
  - For **LinkedIn**: Login is optional but recommended for reliable results. You can disable LinkedIn search (`LINKEDIN_ENABLED=false`) and use Indeed only.

**Note**: LinkedIn has strong anti-scraping measures. The agent will automatically use Selenium (with login) if credentials are provided, otherwise it falls back to basic scraping.

### API-based Platforms (Recommended!)

The agent now supports **legal API-based platforms** that are more reliable than scraping:

#### JSearch API (⭐ Recommended - Free!)

- **What it does**: Aggregates jobs from Google Jobs and other public sources
- **Why use it**: Legal, reliable, no scraping blocks, free tier available
- **How to get**: 
  1. Sign up on [RapidAPI](https://rapidapi.com/letscrape/api/jsearch)
  2. Subscribe to JSearch API (free tier)
  3. Copy your RapidAPI key
  4. Add `JSEARCH_API_KEY=your_key` to `.env`
- **Status**: Enabled by default (`JSEARCH_ENABLED=true`)

#### Adzuna API (Optional)

- **What it does**: Aggregates jobs from multiple sources worldwide
- **Why use it**: Legal, reliable, supports India region
- **How to get**:
  1. Sign up at [Adzuna Developer Portal](https://developer.adzuna.com/)
  2. Get your API key and App ID
  3. Add `ADZUNA_API_KEY`, `ADZUNA_APP_ID` to `.env`
  4. Enable with `ADZUNA_ENABLED=true`

**Benefits of API-based platforms**:
- ✅ Legal and compliant
- ✅ No blocking or 403 errors
- ✅ More reliable data
- ✅ Better structured job information
- ✅ Faster than scraping

**Note**: The agent runs API-based searches first, then falls back to scraping-based platforms. This ensures you always get results even if scraping is blocked!

### Customizing Job Search

Edit `.env` file to customize:

- **Keywords**: Add more job titles or skills
- **Location**: Change to your preferred location
- **User Profile**: Add your skills, experience level, industry, and preferences for better matching
- **Max Jobs**: Adjust the number of jobs to receive

## Project Structure

```
Job Agent AI/
├── job_search_agent.py    # Main agent script
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .env                  # Your environment variables (not in git)
├── .gitignore           # Git ignore rules
├── README.md            # This file
└── .github/
    └── workflows/
        └── job-search.yml # GitHub Actions workflow
```

## How It Works

1. **Job Search**: 
   - **API-based (Legal)**: JSearch API, Adzuna API - aggregates from Google Jobs and other sources
   - **Scraping-based**: Indeed, LinkedIn, Naukri.com, Glassdoor, Hirist, Wellfound (AngelList), JobsLever - uses web scraping
   - Collects job title, company, location, and URL
   - Searches for multiple keywords (Java SpringBoot, Go, React, Software Engineering)
   - **Priority**: API-based searches run first for reliability
   - **Naukri.com** provides excellent coverage for Indian jobs

2. **Location Filtering**:
   - Filters jobs to only include India-based or Remote positions
   - Pan India only: Remote jobs OK, but WFO must be in India
   - Excludes jobs with office locations outside India

3. **AI Filtering**:
   - Sends job listings to Groq API with your complete profile
   - Uses your skills, experience level, and preferences for matching
   - AI filters and ranks jobs based on relevance
   - Returns top N most relevant jobs (SDE-1 level, 1+ years experience)

4. **Email Delivery**:
   - Formats jobs in HTML email (viewable in any email client)
   - **Attaches Excel file** (.xlsx) with all job details for easy filtering and tracking
   - **Attaches PDF file** (.pdf) for easy reading and printing
   - Excel file includes:
     - Job ID, Job Title, Company Name, Location, Source
     - Date Posted, Scraped Date, Job URL (clickable links)
     - Sortable, filterable columns for easy management
   - PDF file includes formatted table with all job information
   - Sends via Gmail SMTP
   - Clean, professional HTML format with clickable apply buttons

## Email Format FAQ

**Q: Will I receive Excel or PDF files with job listings?**

**A:** Yes! You'll receive **BOTH**:
1. **HTML Email** - Clean, readable format with clickable buttons
2. **Excel File (.xlsx)** - Attached for easy filtering, sorting, and tracking applications
3. **PDF File (.pdf)** - Attached for easy reading and printing

**Excel File Includes:**
- **Job ID** (JOB-001, JOB-002, etc.)
- **Job Title** (Role name)
- **Company Name** (Company hiring)
- **Location** (City/Location or Remote)
- **Source** (Indeed, Naukri, or Glassdoor)
- **Date Posted** (When job was posted)
- **Scraped Date** (When we found it)
- **Job URL** (Clickable hyperlink to apply)

**Benefits of Excel File:**
- ✅ Filter by company, location, or source
- ✅ Sort by any column
- ✅ Track which jobs you've applied to
- ✅ Add notes and status columns
- ✅ Easy to manage and organize

**PDF File:**
- Clean, printable format
- All job information in a table
- Perfect for saving or sharing

## Troubleshooting

### Common Issues

**1. "Missing required configuration" error**
- Ensure all required variables are set in `.env`
- Check that `.env` file exists and is in the project root

**2. "Authentication failed" for Gmail**
- Verify you're using App Password, not regular password
- Ensure 2-Step Verification is enabled
- Check Gmail username is correct

**3. "Rate limit exceeded" for Groq API**
- Free tier has rate limits
- Reduce `MAX_JOBS` or add delay between runs

**4. No jobs found**
- Check internet connection
- Verify job keywords are correct
- LinkedIn may have anti-scraping measures (temporary issue)

**5. Web scraping not working**
- Sites may have updated their HTML structure
- Check logs for parsing errors
- Update selectors in `job_search_agent.py` if needed

### Logs

Check `job_search.log` for detailed execution logs:

```bash
tail -f job_search.log
```

## Limitations

- **LinkedIn Scraping**: LinkedIn has strong anti-scraping measures. Basic scraping may not always work. Consider using LinkedIn API (requires approval) for production use.
- **Naukri.com**: Naukri.com is an excellent source for Indian jobs. The scraping implementation supports both API endpoints and HTML parsing for reliability.
- **Rate Limits**: Free APIs have rate limits. Adjust `REQUEST_DELAY` if needed.
- **HTML Changes**: Web scraping relies on HTML structure. Sites may update, requiring code changes.

## Security & Privacy

**⚠️ IMPORTANT: Security is our top priority!**

### ✅ What the Agent Does (Read-Only):
- Searches and reads job listings
- Filters jobs using AI
- Sends results via email
- **NEVER posts, updates, or modifies anything**

### 🔒 Credentials Safety:
- `.env` file is in `.gitignore` - never committed to git
- GitHub Secrets are encrypted (if using GitHub Actions)
- Credentials stored locally only on your machine

### 🛡️ Platform Requirements:
- **Naukri.com**: ✅ No credentials needed
- **Indeed**: ✅ No credentials needed  
- **LinkedIn**: ⚠️ Credentials optional (read-only operations)

### 📋 Recommendations:
1. **Safest Option**: Use Indeed + Naukri only (disable LinkedIn)
   - Set `LINKEDIN_ENABLED=false` in `.env`
   - No credentials needed, excellent coverage!

2. **If Using LinkedIn**: The code is read-only and safe
   - Only reads job listings
   - Never posts or modifies anything
   - Browser closes immediately after reading

3. **Review Code**: You can verify safety yourself
   - Check `job_search_agent.py` - only read operations
   - See `SECURITY.md` for detailed security guide

**For detailed security information, see [SECURITY.md](SECURITY.md)**

## Contributing

Feel free to submit issues and pull requests!

## License

This project is open source and available for personal use.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review logs in `job_search.log`
3. Open an issue on GitHub

## Future Enhancements

- [ ] Add more job sites (Glassdoor, Monster, etc.)
- [ ] Implement LinkedIn API integration
- [ ] Add job application tracking
- [ ] Support multiple email recipients
- [ ] Add webhook notifications
- [ ] Implement job deduplication across sites
- [ ] Add salary range filtering

---

**Happy Job Hunting! 🎯**

