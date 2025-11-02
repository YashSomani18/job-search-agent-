# GitHub Actions Deployment Checklist ✅

## Quick Summary

**GitHub Actions is FREE and unlimited** for public repositories!
- ✅ No limits to worry about
- ✅ No monitoring needed
- ✅ No AWS account required
- ✅ Runs daily automatically

## Step-by-Step Deployment

### 1️⃣ Push Code to GitHub

```bash
# Initialize git (if not done)
git init

# Add all files
git add .

# Commit
git commit -m "Job Search Agent - Ready for GitHub Actions"

# Create repository on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### 2️⃣ Add GitHub Secrets

Go to: **Repository → Settings → Secrets and variables → Actions → New repository secret**

**Add these Required Secrets:**

1. `GROQ_API_KEY` = `YOUR_GROQ_API_KEY` (from your .env file)
2. `GMAIL_USER` = `YOUR_GMAIL_USER` (from your .env file)
3. `GMAIL_APP_PASSWORD` = `YOUR_GMAIL_APP_PASSWORD` (from your .env file)
4. `EMAIL_TO` = `yashsomani1806@gmail.com`
5. `JOB_KEYWORDS` = `Java Developer,SpringBoot Developer,Go Developer,React Developer,Software Engineer,Backend Developer,SDE-1,Software Developer Engineer,Software Engineering,SDE-2,SDE-II,Frontend Developer`
6. `JOB_LOCATION` = `India`
7. `JSEARCH_API_KEY` = `YOUR_JSEARCH_API_KEY` (from your .env file)

**Add these Recommended Secrets (for better job matching):**

8. `USER_SKILLS` = `Java, SpringBoot, Spring Data JPA, Kafka, AWS S3, Docker, PostgreSQL, MySQL, Redis, MongoDB, React.js, Node.js, Express.js, Python, SQL, Git, Jenkins, Maven, Lombok`
9. `USER_EXPERIENCE_LEVEL` = `Mid`
10. `USER_YEARS_EXPERIENCE` = `1.5`
11. `USER_CURRENT_ROLE` = `SDE-1`
12. `USER_INDUSTRY` = `Tech,Software Engineering,Backend Development`
13. `USER_PREFERENCES` = `Pan India only, Remote jobs fine, WFO must be in India`

**Optional (have defaults):**

14. `GROQ_MODEL` = `llama-3.3-70b-versatile` (optional - already set as default)
15. `JSEARCH_MAX_DAILY_REQUESTS` = `10` (test mode - change to 6 after testing)
16. `MAX_JOBS` = `100` (optional - already set as default)

### 3️⃣ Test the Workflow

1. Go to **Actions** tab in your GitHub repository
2. You should see "Daily Job Search" workflow
3. Click **Run workflow** → **Run workflow** (manual trigger)
4. Wait for it to complete (~2-5 minutes)
5. Check your email for job listings!

### 4️⃣ Verify Daily Schedule

The workflow is set to run **daily at 8:00 AM IST (2:30 UTC)**.

You'll receive an email every day at 8 AM IST with job listings!

## Important Notes

✅ **GitHub Actions is FREE** - No limits to monitor
✅ **Groq API is FREE** - No limits to monitor (we're using free tier)
✅ **JSearch API** - Free tier: 200 requests/month (we're using 10/day = 300/month for testing, will reduce to 6/day = 180/month after testing)
✅ **Gmail SMTP** - Free to send emails

## Troubleshooting

- **Workflow not running?** → Check Actions tab for errors
- **No email received?** → Check Gmail spam folder
- **Error in logs?** → Check Actions → Run → Logs section
- **Secrets missing?** → Make sure all required secrets are added

## That's It! 🎉

Once you've added all secrets and pushed the code, the workflow will run automatically every day at 8 AM IST!

