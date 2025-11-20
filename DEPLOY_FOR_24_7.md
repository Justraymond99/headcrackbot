# 🚀 Deploy for True 24/7 Operation

## The Problem
Running locally means your Mac needs to stay on 24/7. That's not ideal!

## The Solution: Deploy to Cloud ☁️

Deploy to a cloud service so it runs 24/7 without your computer.

---

## Option 1: Railway.app (Easiest - Recommended) ⭐

**Free tier available!** Runs 24/7, no credit card needed for basic usage.

### Quick Setup (10 minutes):

1. **Push to GitHub** (if not already):
   ```bash
   cd "/Users/yungray/Desktop/chess game/tictactoe"
   git init
   git add .
   git commit -m "Ready for Railway deployment"
   git branch -M main
   # Create repo on GitHub, then:
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```

2. **Sign up at Railway**:
   - Go to [railway.app](https://railway.app)
   - Click "Login" → Sign in with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

3. **Add Environment Variables**:
   In Railway dashboard → **Variables** tab, add:
   ```
   TELEGRAM_BOT_TOKEN=8506045290:AAGm8d-kYJoBOtgwsNJalE_kZicAgDPFZXs
   TELEGRAM_CHAT_ID=7197338861
   ODDS_API_KEY=your_odds_api_key
   SPORTSDATA_API_KEY=your_sportsdata_key
   PICKS_SPORTS=NBA,NFL,MLB,NHL,UFC,BOXING
   PICKS_MIN_EV=0.05
   PICKS_MIN_CONFIDENCE=0.6
   PICKS_MAX_COUNT=5
   PARLAYS_MIN_CONFIDENCE=0.5
   PARLAYS_MAX_PER_SPORT=1
   ```

4. **Set Start Command**:
   - Go to **Settings** tab
   - Under **Deploy**, set **Start Command**:
     ```
     python enhanced_scheduler.py
     ```
   - Click **Save**

5. **Done!** Railway will deploy and run 24/7 automatically.

**Cost:** Free tier includes $5/month credit (usually enough for this)

---

## Option 2: Heroku (Alternative)

Similar to Railway, also has a free tier (with limitations).

See `DEPLOYMENT_GUIDE.md` for detailed instructions.

---

## Option 3: Keep Running Locally

If you want to keep it local:

**Pros:**
- No cloud costs
- Full control

**Cons:**
- Mac must stay on 24/7
- Uses electricity
- Stops if Mac restarts/sleeps

**To keep Mac awake:**
- System Preferences → Energy Saver → Prevent computer from sleeping
- Or use `caffeinate` command:
  ```bash
  caffeinate -d
  ```

---

## Recommendation

**Deploy to Railway** - it's free, easy, and runs 24/7 without any maintenance!

Your picks will keep coming even when your Mac is off, sleeping, or restarted.

---

## After Deployment

Once deployed, you can:
- Stop the local scheduler: `./stop_scheduler.sh`
- Your picks will now come from the cloud 24/7
- Check Railway dashboard for logs and status

