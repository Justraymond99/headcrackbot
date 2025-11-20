# 🚂 Railway Deployment Guide - Step by Step

## Quick Setup (10 minutes)

### Step 1: Commit All Changes

```bash
cd "/Users/yungray/Desktop/chess game/tictactoe"
git add -A
git commit -m "Setup Telegram notifications and Railway deployment"
```

### Step 2: Push to GitHub

**If you don't have a GitHub repo yet:**

1. Go to [github.com/new](https://github.com/new)
2. Repository name: `hourly-picks-scheduler` (or any name you want)
3. Choose **Private** (recommended)
4. **DO NOT** check "Initialize with README"
5. Click **"Create repository"**

**Then push:**
```bash
git remote add origin https://github.com/YOUR_USERNAME/hourly-picks-scheduler.git
git branch -M main
git push -u origin main
```

**If you already have a repo:**
```bash
git push origin main
```

### Step 3: Deploy to Railway

1. **Sign up at Railway:**
   - Go to [railway.app](https://railway.app)
   - Click **"Login"** → **"Start a New Project"**
   - Sign in with **GitHub**

2. **Create New Project:**
   - Click **"New Project"**
   - Select **"Deploy from GitHub repo"**
   - Choose your repository (`hourly-picks-scheduler`)

3. **Railway will auto-detect Python and start deploying!**

### Step 4: Add Environment Variables

In Railway dashboard → **Variables** tab → Click **"+ New Variable"** for each:

**Required:**
```
TELEGRAM_BOT_TOKEN=8506045290:AAGm8d-kYJoBOtgwsNJalE_kZicAgDPFZXs
TELEGRAM_CHAT_ID=7197338861
ODDS_API_KEY=your_odds_api_key_here
SPORTSDATA_API_KEY=your_sportsdata_key_here
```

**Optional (with defaults):**
```
PICKS_SPORTS=NBA,NFL,MLB,NHL,UFC,BOXING
PICKS_MIN_EV=0.05
PICKS_MIN_CONFIDENCE=0.6
PICKS_MAX_COUNT=5
PARLAYS_MIN_CONFIDENCE=0.5
PARLAYS_MAX_PER_SPORT=1
SEND_PICKS_ON_STARTUP=false
```

### Step 5: Set Start Command

1. Go to **Settings** tab
2. Under **Deploy**, find **"Start Command"**
3. Set it to:
   ```
   python enhanced_scheduler.py
   ```
4. Click **Save**

Railway will automatically redeploy!

### Step 6: Initialize Database

After first deployment, you need to initialize the database. Railway will run this automatically, but you can also do it manually:

1. Go to Railway dashboard → **Deployments** tab
2. Click on the latest deployment
3. Go to **Logs** tab
4. You should see database initialization messages

**Or run manually via Railway CLI:**
```bash
railway run python init_database.py
```

### Step 7: Verify It's Running

1. Go to **Deployments** tab
2. Check **Logs** - you should see:
   ```
   INFO:__main__:Scheduler started with all features enabled.
   INFO:apscheduler.scheduler:Scheduler started
   ```

3. Wait for the next hour (:00 or :30) and check Telegram for picks!

---

## ✅ You're Done!

Your scheduler is now running 24/7 on Railway!

### Monitor Your Deployment

- **Logs**: Railway dashboard → Deployments → View Logs
- **Metrics**: Railway dashboard → Metrics tab (CPU, Memory, Network)
- **Status**: Railway dashboard → Deployments tab

### Update Code

Just push to GitHub:
```bash
git add .
git commit -m "Update"
git push
```

Railway auto-deploys! 🎉

---

## 💰 Pricing

**Free Tier:**
- $5 credit/month
- 500 hours/month (enough for always-on)
- No credit card needed

**Pro ($5/month):**
- Always-on (never sleeps)
- Better performance
- Worth it for production

---

## 🚨 Troubleshooting

### Service won't start?
- Check **Deployments** → **Logs** for errors
- Verify all environment variables are set
- Check start command: `python enhanced_scheduler.py`

### Database errors?
- Run: `railway run python init_database.py`
- Check logs for initialization errors

### Not receiving picks?
- Verify Telegram credentials in **Variables**
- Check Railway logs for Telegram errors
- Make sure you've messaged the bot on Telegram

### Want to test immediately?
- Set `SEND_PICKS_ON_STARTUP=true` temporarily
- Check logs to see first picks being sent

---

## 📱 Next Steps

1. ✅ Deploy to Railway
2. ✅ Add environment variables
3. ✅ Initialize database
4. ✅ Wait for first picks (next hour)
5. 🎉 Enjoy 24/7 picks!

**Your system is now running in the cloud!** 🚀

