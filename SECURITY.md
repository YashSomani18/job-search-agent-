# Security & Privacy Guide

## Credentials Storage & Safety

### ✅ Your Credentials Are Secure

1. **Local Storage (.env file)**:
   - All credentials are stored in `.env` file
   - `.env` file is in `.gitignore` - **NEVER committed to git**
   - Only you have access to this file on your local machine
   - Never share `.env` file with anyone

2. **GitHub Actions (if deployed)**:
   - Credentials are stored as **GitHub Secrets**
   - GitHub Secrets are encrypted and only accessible to repository admins
   - Secrets are never exposed in logs or code
   - Only used during workflow execution

## What the Agent Does (Read-Only Operations)

### ✅ Safe Operations - What the Agent DOES:

1. **Job Search (Read-Only)**:
   - Searches job listings on Indeed, LinkedIn, Naukri
   - Reads job titles, companies, locations, URLs
   - Filters jobs using AI
   - Sends results via email

2. **LinkedIn (If credentials provided)**:
   - Logs in to LinkedIn (one time per run)
   - Navigates to job search page
   - **ONLY READS** job listing data
   - Closes browser immediately after reading

### ❌ What the Agent DOES NOT Do:

The agent **NEVER**:
- Posts anything to LinkedIn
- Updates your LinkedIn profile
- Likes, comments, or shares posts
- Sends messages to anyone
- Applies to jobs automatically
- Modifies any data on any platform
- Accesses your personal messages or connections
- Changes your account settings

## Platform Requirements

### Naukri.com ✅
- **NO CREDENTIALS NEEDED**
- Uses public web scraping
- No login required
- Safe and secure

### Indeed ✅
- **NO CREDENTIALS NEEDED**
- Uses public web scraping
- No login required
- Safe and secure

### LinkedIn ⚠️
- **CREDENTIALS OPTIONAL**
- Works without login (limited results)
- Can use login for better results (read-only)
- **You can disable LinkedIn** if concerned

## How to Disable LinkedIn (If You're Concerned)

### Option 1: Disable in .env file
```bash
LINKEDIN_ENABLED=false
```

### Option 2: Don't provide LinkedIn credentials
- Leave `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD` empty in `.env`
- The agent will automatically use basic scraping (no login)

## Code Review - Verification

You can verify the code yourself:
1. Check `job_search_agent.py` - LinkedIn search function
2. Search for keywords: `post`, `update`, `like`, `comment`, `share`, `message`, `apply`
3. You'll find **ZERO write operations** - only read operations

## Best Practices

1. **Never commit .env file** (already in `.gitignore`)
2. **Use strong passwords** for LinkedIn
3. **Review code** before running (if concerned)
4. **Disable LinkedIn** if you prefer not to provide credentials
5. **Use GitHub Secrets** for GitHub Actions (encrypted)

## If You're Still Concerned

**Recommended Approach**:
1. Use **Indeed** + **Naukri.com** only (no credentials needed)
2. Disable LinkedIn: `LINKEDIN_ENABLED=false`
3. This gives you excellent job coverage without any credentials

Indeed and Naukri.com together provide excellent coverage for Indian jobs!

## Questions?

If you have security concerns:
1. Review the code in `job_search_agent.py`
2. Check that only read operations are performed
3. Disable LinkedIn if preferred
4. Use Indeed + Naukri (no credentials needed)

---

**Remember**: Your security is our priority. The agent is designed to be read-only and safe.

