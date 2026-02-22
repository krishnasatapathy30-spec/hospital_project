# Deploying the Hospital Project (stable URL)

Option A — Render.com (recommended, free tier with stable URL):

1. Create a GitHub repository and push this project (see below).
2. Sign in to Render and create a new Web Service.
   - Connect your GitHub account and select the repo.
   - Environment: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Set environment variable `SECRET_KEY` to a secure value.
3. Deploy — Render will provide a stable URL like `your-service.onrender.com`.

Option B — Railway / Fly.io / PythonAnywhere:
- Similar: push repo, connect provider, set build/start commands.

Prepare & push (locally):

```powershell
git init
git add .
git commit -m "Prepare app for deployment"
# create a repo on GitHub (or use create_github_repo.ps1 with your GITHUB_TOKEN)
git remote add origin https://github.com/<youruser>/<repo>.git
git push -u origin main
```

If you want, provide a `GITHUB_TOKEN` here and I can create the repo and push for you.

Notes:
- A paid ngrok plan is required for a permanent reserved subdomain. Free ngrok URLs change each run.
- This repository already includes a `Procfile` and `requirements.txt` suitable for Render.
