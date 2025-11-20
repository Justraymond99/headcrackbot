# 🚀 Quick Railway Setup - Copy & Paste

## ✅ Your Code is Ready!

Git is initialized and committed. Now follow these steps:

---

## 📋 Step 1: Create GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. Repository name: `hourly-picks-scheduler`
3. Description: `24/7 Hourly Sports Betting Picks`
4. Choose: **Private** (recommended)
5. **DO NOT** check "Initialize with README"
6. Click **"Create repository"**

---

## 📤 Step 2: Push to GitHub

Copy and paste these commands (replace YOUR_USERNAME):

```bash
cd "/Users/yungray/Desktop/chess game/tictactoe"
git remote add origin https://github.com/YOUR_USERNAME/hourly-picks-scheduler.git
git branch -M main
git push -u origin main
```

**Replace `YOUR_USERNAME` with your actual GitHub username!**

---

## 🚂 Step 3: Deploy to Railway

1. **Sign up:** [railway.app](https://railway.app) → Login with GitHub
2. **New Project:** Click "New Project" → "Deploy from GitHub repo"
3. **Select Repo:** Choose `hourly-picks-scheduler`
4. **Deploy:** Click "Deploy Now" (it will auto-detect Python)

---

## ⚙️ Step 4: Add Environment Variables

In Railway, go to **Variables** tab and add these (click "+ New Variable" for each):

```
ODDS_API_KEY=your_odds_api_key_here
SPORTSDATA_API_KEY=your_sportsdata_key_here
TWILIO_ACCOUNT_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_token_here
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

**Important:** Replace all placeholder values with your actual API keys!

---

## 🎯 Step 5: Set Start Command

1. Go to **Settings** tab in Railway
2. Find **"Start Command"** field
3. Enter: `python enhanced_scheduler.py`
4. Click **Save**

Railway will automatically redeploy!

---

## ✅ Step 6: Verify It's Running

1. Go to **Deployments** tab
2. Click latest deployment → **View Logs**
3. Look for: `Starting enhanced hourly picks scheduler...`
4. Look for: `Scheduler started with all features enabled.`

---

## 🎉 Done!

Your picks will now run 24/7! 

- Every hour at :00 → Individual picks
- Every hour at :30 → Best parlay from each sport

---

## 🚨 Quick Troubleshooting

**Not working?**
- Check Railway logs
- Verify all environment variables are set
- Make sure Twilio credentials are correct

**Not receiving texts?**
- Verify `USER_PHONE_NUMBER` format: `+1234567890`
- Check Twilio dashboard
- Check Railway logs for errors

---

## 📱 Need Help?

Check `RAILWAY_SETUP_STEPS.md` for detailed instructions!

