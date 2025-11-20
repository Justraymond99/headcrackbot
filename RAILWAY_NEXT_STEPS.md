# 🚂 Railway Deployment - Next Steps

## ✅ Code Pushed to GitHub!

Your code is now at: https://github.com/Justraymond99/headcrackbot.git

---

## Step 1: Deploy to Railway

1. **Go to Railway:**
   - Visit: https://railway.app
   - Click **"Login"** → Sign in with **GitHub**

2. **Create New Project:**
   - Click **"New Project"**
   - Select **"Deploy from GitHub repo"**
   - Find and select: **`headcrackbot`** (or search for `Justraymond99/headcrackbot`)
   - Click **"Deploy"**

3. **Railway will automatically:**
   - Detect Python
   - Start building your project
   - Deploy it

---

## Step 2: Add Environment Variables

Once deployed, go to **Variables** tab and add:

### Required Variables:

```
TELEGRAM_BOT_TOKEN=8506045290:AAGm8d-kYJoBOtgwsNJalE_kZicAgDPFZXs
TELEGRAM_CHAT_ID=7197338861
ODDS_API_KEY=your_odds_api_key_here
SPORTSDATA_API_KEY=your_sportsdata_key_here
```

### Optional Variables (with defaults):

```
PICKS_SPORTS=NBA,NFL,MLB,NHL,UFC,BOXING
PICKS_MIN_EV=0.05
PICKS_MIN_CONFIDENCE=0.6
PICKS_MAX_COUNT=5
PARLAYS_MIN_CONFIDENCE=0.5
PARLAYS_MAX_PER_SPORT=1
SEND_PICKS_ON_STARTUP=false
```

**How to add:**
- Click **"+ New Variable"** for each one
- Paste the name and value
- Click **"Add"**

---

## Step 3: Set Start Command

1. Go to **Settings** tab
2. Scroll to **"Deploy"** section
3. Find **"Start Command"** field
4. Enter:
   ```
   python enhanced_scheduler.py
   ```
5. Click **"Save"**

Railway will automatically redeploy with the new start command.

---

## Step 4: Initialize Database

After the first deployment, the database needs to be initialized:

1. Go to **Deployments** tab
2. Click on the latest deployment
3. Go to **Logs** tab
4. You should see database initialization messages

**If you see database errors:**
- Go to Railway dashboard
- Click on your service
- Go to **"Deployments"** → **"View Logs"**
- Or use Railway CLI:
  ```bash
  railway run python init_database.py
  ```

---

## Step 5: Verify It's Running

1. **Check Logs:**
   - Go to **Deployments** tab
   - Click **"View Logs"**
   - You should see:
     ```
     INFO:__main__:Scheduler started with all features enabled.
     INFO:apscheduler.scheduler:Scheduler started
     ```

2. **Wait for First Picks:**
   - Picks are sent every hour at :00 and :30
   - Check Telegram for your first picks!

---

## Step 6: Stop Local Scheduler (Optional)

Once Railway is running, you can stop the local scheduler:

```bash
./stop_scheduler.sh
```

Your picks will now come from Railway 24/7!

---

## Monitoring

- **Logs**: Railway dashboard → Deployments → View Logs
- **Metrics**: Railway dashboard → Metrics tab (CPU, Memory)
- **Status**: Railway dashboard → Deployments tab

---

## Troubleshooting

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

## 💰 Railway Pricing

**Free Tier:**
- $5 credit/month
- 500 hours/month (enough for always-on)
- No credit card needed

**Pro ($5/month):**
- Always-on (never sleeps)
- Better performance
- Worth it for production

---

## ✅ You're All Set!

Once deployed, your scheduler will run 24/7 in the cloud!

**Next:** Go to https://railway.app and deploy! 🚀

