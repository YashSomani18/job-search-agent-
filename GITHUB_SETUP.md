# GitHub Actions Setup Guide

## Step 1: Push Code to GitHub

1. Initialize git repository (if not already done):
```bash
git init
git add .
git commit -m "Initial commit: Job Search Agent"
```

2. Create a new repository on GitHub (e.g., `job-search-agent`)

3. Push to GitHub:
```bash
git remote add origin https://github.com/YOUR_USERNAME/job-search-agent.git
git push -u origin main
```

## Step 2: Add GitHub Secrets

Go to your GitHub repository:
1. Click **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add each secret one by one:

### Required Secrets:

**GROQ_API_KEY**
- Name: `GROQ_API_KEY`
- Value: `YOUR_GROQ_API_KEY` (from your .env file)

**GMAIL_USER**
- Name: `GMAIL_USER`
- Value: `yashsomani1806@gmail.com`

**GMAIL_APP_PASSWORD**
- Name: `GMAIL_APP_PASSWORD`
- Value: `YOUR_GMAIL_APP_PASSWORD` (from your .env file)

**EMAIL_TO**
- Name: `EMAIL_TO`
- Value: `yashsomani1806@gmail.com`

**JOB_KEYWORDS**
- Name: `JOB_KEYWORDS`
- Value: `Java Developer,SpringBoot Developer,Go Developer,React Developer,Software Engineer,Backend Developer,SDE-1,Software Developer Engineer,Software Engineering,SDE-2,SDE-II,Frontend Developer`

**JOB_LOCATION**
- Name: `JOB_LOCATION`
- Value: `India`

### Recommended Secrets (ADD THESE FOR BETTER MATCHING):

**⚠️ IMPORTANT: Add these secrets for better job matching! They are now integrated into the workflow.**

**USER_SKILLS**
- Name: `USER_SKILLS`
- Value: `Java, SpringBoot, Spring Data JPA, Kafka, AWS S3, Docker, PostgreSQL, MySQL, Redis, MongoDB, React.js, Node.js, Express.js, Python, SQL, Git, Jenkins, Maven, Lombok`

**USER_EXPERIENCE_LEVEL**
- Name: `USER_EXPERIENCE_LEVEL`
- Value: `Mid`

**USER_YEARS_EXPERIENCE**
- Name: `USER_YEARS_EXPERIENCE`
- Value: `1.5`

**USER_CURRENT_ROLE**
- Name: `USER_CURRENT_ROLE`
- Value: `SDE-1`

**USER_INDUSTRY**
- Name: `USER_INDUSTRY`
- Value: `Tech,Software Engineering,Backend Development`

**USER_PREFERENCES**
- Name: `USER_PREFERENCES`
- Value: `Pan India only, Remote jobs fine, WFO must be in India, SDE-1 level, 1+ years experience, Java SpringBoot or Go or React`

### Optional Secrets:

**MAX_JOBS** (default: 100)
- Name: `MAX_JOBS`
- Value: `100`

**GROQ_MODEL** (default: llama-3.3-70b-versatile - Updated from decommissioned model)
- Name: `GROQ_MODEL`
- Value: `llama-3.3-70b-versatile`

**JSEARCH_API_KEY** (Required for API-based job search - Recommended!)
- Name: `JSEARCH_API_KEY`
- Value: `YOUR_JSEARCH_API_KEY` (from your .env file)

**JSEARCH_MAX_DAILY_REQUESTS** (Test mode - change back to 6 after testing)
- Name: `JSEARCH_MAX_DAILY_REQUESTS`
- Value: `10`

**LINKEDIN_ENABLED** (default: true)
- Name: `LINKEDIN_ENABLED`
- Value: `true`

**INDEED_ENABLED** (default: true)
- Name: `INDEED_ENABLED`
- Value: `true`

**JSEARCH_ENABLED** (default: true - Recommended! Uses API, more reliable)
- Name: `JSEARCH_ENABLED`
- Value: `true`

## Step 3: Verify Workflow

1. Go to **Actions** tab in your GitHub repository
2. You should see the "Daily Job Search" workflow
3. You can manually trigger it by clicking **Run workflow**

## Step 4: Wait for Daily Runs

The workflow will automatically run **every day at 8:00 AM IST (2:30 UTC)**.

You'll receive emails with job listings in your inbox!

## Troubleshooting

- Check **Actions** tab for workflow runs
- View logs if workflow fails
- Ensure all secrets are added correctly
- Check that `.env` file is NOT committed (it's in `.gitignore`)

