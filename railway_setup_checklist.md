# ✅ Railway Deployment Checklist

## Pre-Deployment ✅

- [x] Code committed to git
- [x] Database initialization script created (`init_database.py`)
- [x] Procfile configured (`worker: python enhanced_scheduler.py`)
- [x] Requirements.txt up to date
- [x] Railway.json configured
- [ ] GitHub repository created
- [ ] Code pushed to GitHub

## Railway Setup Steps

### 1. Create GitHub Repo (if needed)
- [ ] Go to https://github.com/new
- [ ] Name: `hourly-picks-scheduler`
- [ ] Private (recommended)
- [ ] Don't initialize with README
- [ ] Create repository

### 2. Push to GitHub
```bash
./push_to_github.sh
```
Or manually:
```bash
git remote add origin https://github.com/YOUR_USERNAME/hourly-picks-scheduler.git
git branch -M main
git push -u origin main
```

### 3. Deploy to Railway
- [ ] Go to https://railway.app
- [ ] Sign in with GitHub
- [ ] New Project → Deploy from GitHub repo
- [ ] Select your repository
- [ ] Wait for auto-deployment

### 4. Add Environment Variables
In Railway → Variables tab, add:

**Required:**
- [ ] `TELEGRAM_BOT_TOKEN=your_new_botfather_token`
- [ ] `TELEGRAM_ALLOWED_CHAT_IDS=your_numeric_chat_id`
- [ ] `ODDS_API_KEY=your_key_here`
- [ ] `SPORTSDATA_API_KEY=your_key_here`

**Optional (with defaults):**
- [ ] `PICKS_SPORTS=NBA,NFL,MLB,NHL,UFC,BOXING`
- [ ] `PICKS_MIN_EV=0.05`
- [ ] `PICKS_MIN_CONFIDENCE=0.6`
- [ ] `PICKS_MAX_COUNT=5`
- [ ] `PARLAYS_MIN_CONFIDENCE=0.5`
- [ ] `PARLAYS_MAX_PER_SPORT=1`

### 5. Set Start Command
- [ ] Go to Settings tab
- [ ] Set Start Command: `python enhanced_scheduler.py`
- [ ] Save

### 6. Initialize Database
- [ ] Check Deployments → Logs
- [ ] Should see database initialization
- [ ] If errors, run: `railway run python init_database.py`

### 7. Verify Running
- [ ] Check Deployments → Logs
- [ ] Should see: "Scheduler started with all features enabled"
- [ ] Wait for next hour (:00 or :30)
- [ ] Check Telegram for picks!

## Post-Deployment

- [ ] Stop local scheduler: `./stop_scheduler.sh`
- [ ] Monitor Railway logs
- [ ] Test Telegram notifications
- [ ] Verify picks are being sent

## Troubleshooting

**Service won't start?**
- Check logs for errors
- Verify all env vars are set
- Check start command

**Database errors?**
- Run: `railway run python init_database.py`
- Check logs

**Not receiving picks?**
- Verify Telegram credentials
- Check Railway logs
- Make sure you messaged the bot

---

**You're all set! Your picks will run 24/7 in the cloud!** 🚀

