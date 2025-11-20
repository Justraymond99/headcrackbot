# 🚀 Railway Setup - Step by Step

## ✅ Step 1: Git is Ready!

Your code is now initialized with git. Next steps:

## 📋 Step 2: Push to GitHub

### Option A: Create New GitHub Repo (Recommended)

1. **Go to GitHub:**
   - Visit [github.com](https://github.com) and sign in
   - Click **"New"** (or the **+** icon) → **"New repository"**

2. **Create Repository:**
   - **Repository name:** `hourly-picks-scheduler` (or any name)
   - **Description:** "24/7 Hourly Sports Betting Picks"
   - **Visibility:** Private (recommended) or Public
   - **DO NOT** initialize with README (we already have files)
   - Click **"Create repository"**

3. **Push Your Code:**
   ```bash
   cd "/Users/yungray/Desktop/chess game/tictactoe"
   git remote add origin https://github.com/YOUR_USERNAME/hourly-picks-scheduler.git
   git push -u origin main
   ```
   
   Replace `YOUR_USERNAME` with your GitHub username!

### Option B: Already Have a Repo?

If you already created the repo on GitHub, just run:
```bash
cd "/Users/yungray/Desktop/chess game/tictactoe"
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

## 🚂 Step 3: Deploy to Railway

1. **Sign Up:**
   - Go to [railway.app](https://railway.app)
   - Click **"Login"** → **"Start a New Project"**
   - Sign in with **GitHub** (easiest way)

2. **Create New Project:**
   - Click **"New Project"** button
   - Select **"Deploy from GitHub repo"**
   - Find and select your `hourly-picks-scheduler` repository
   - Click **"Deploy Now"**

3. **Wait for Deploy:**
   - Railway will automatically detect Python
   - It will install dependencies from `requirements.txt`
   - Watch the deployment logs!

## ⚙️ Step 4: Add Environment Variables

1. **Go to Variables Tab:**
   - In your Railway project, click **"Variables"** tab
   - Click **"+ New Variable"**

2. **Add Each Variable:**
   
   Click **"+ New Variable"** for each of these:

   ```
   ODDS_API_KEY=your_odds_api_key
   SPORTSDATA_API_KEY=your_sportsdata_key
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   TWILIO_PHONE_NUMBER=+1234567890
   USER_PHONE_NUMBER=+1234567890
   DATABASE_URL=sqlite:///hourly_picks.db
   PICKS_SPORTS=NBA,NFL,MLB,NHL,UFC,BOXING
   DEFAULT_SPORTS=NBA,NFL,MLB,NHL,UFC,BOXING
   PICKS_MIN_EV=0.05
   PICKS_MIN_CONFIDENCE=0.6
   PICKS_MAX_COUNT=5
   PARLAYS_MIN_CONFIDENCE=0.5
   PARLAYS_MAX_PER_SPORT=1
   ```

   **Important:** Replace all the placeholder values with your actual API keys!

3. **Where to Get API Keys:**
   - **ODDS_API_KEY:** [the-odds-api.com](https://the-odds-api.com)
   - **SPORTSDATA_API_KEY:** [sportsdata.io](https://sportsdata.io) (optional)
   - **Twilio:** [twilio.com/console](https://twilio.com/console)

## 🎯 Step 5: Set Start Command

1. **Go to Settings:**
   - Click **"Settings"** tab in Railway
   - Scroll to **"Deploy"** section

2. **Set Start Command:**
   - Find **"Start Command"** field
   - Enter: `python enhanced_scheduler.py`
   - Click **"Save"**

   Railway will automatically redeploy!

## ✅ Step 6: Verify It's Running

1. **Check Deployments:**
   - Go to **"Deployments"** tab
   - Click on the latest deployment
   - Click **"View Logs"**

2. **What to Look For:**
   - Should see: `Starting enhanced hourly picks scheduler...`
   - Should see: `Scheduler started with all features enabled.`
   - No error messages!

3. **Test It:**
   - Wait for the next hour (:00 or :30)
   - Check your phone for picks!

## 📱 Step 7: Monitor (Optional)

- **View Logs:** Railway dashboard → Deployments → View Logs
- **Set Up Alerts:** Railway can email you on errors
- **Check Metrics:** See CPU/Memory usage

## 🎉 You're Done!

Your hourly picks scheduler is now running 24/7 in the cloud!

### What Happens Now:
- ✅ Every hour at :00 → Sends individual picks
- ✅ Every hour at :30 → Sends best parlay from each sport
- ✅ Automatically runs forever (until you stop it)

### Update Your Code:
Just push to GitHub:
```bash
git add .
git commit -m "Update"
git push
```
Railway auto-deploys! 🚀

---

## 🚨 Troubleshooting

### Deployment Fails?
- Check logs in Railway dashboard
- Verify all environment variables are set
- Make sure `requirements.txt` is correct

### Service Won't Start?
- Check start command: `python enhanced_scheduler.py`
- Check logs for Python errors
- Verify database URL format

### Not Receiving Texts?
- Verify Twilio credentials
- Check phone number format: `+1234567890`
- Check Railway logs for Twilio errors
- Verify `USER_PHONE_NUMBER` is set

### Need Help?
- Check Railway logs first
- Verify all environment variables
- Make sure Twilio is configured correctly

---

**Your picks will now run 24/7! 🎯**

