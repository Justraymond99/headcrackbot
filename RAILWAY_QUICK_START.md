# Railway.app Quick Start (5 Minutes) ⚡

## The Easiest Way to Deploy 24/7

### Step 1: Push to GitHub (if not already)
```bash
cd /Users/yungray/Desktop/chess\ game/tictactoe
git init
git add .
git commit -m "Ready for Railway deployment"
git branch -M main
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

### Step 2: Sign Up at Railway
1. Go to [railway.app](https://railway.app)
2. Click "Login" → "Start a New Project"
3. Sign in with GitHub

### Step 3: Deploy
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your repository
4. Railway will auto-detect Python and deploy!

### Step 4: Add Environment Variables
1. Go to your project → **Variables** tab
2. Click **+ New Variable**
3. Add each variable (copy from `.env.example`):

```
ODDS_API_KEY=your_key
SPORTSDATA_API_KEY=your_key
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890
USER_PHONE_NUMBER=+1234567890
DATABASE_URL=sqlite:///hourly_picks.db
PICKS_SPORTS=NBA,NFL,MLB,NHL,UFC,BOXING
```

### Step 5: Set Start Command
1. Go to **Settings** tab
2. Under **Deploy**, set **Start Command**:
   ```
   python enhanced_scheduler.py
   ```
3. Click **Save**

### Step 6: Deploy!
1. Railway will automatically redeploy
2. Go to **Deployments** tab to see logs
3. Watch it start up! 🚀

## ✅ You're Done!

Your hourly picks scheduler is now running 24/7!

### Check Status
- **Deployments** tab → See logs
- **Metrics** tab → See CPU/Memory usage

### View Logs
```bash
railway logs
```
Or click **View Logs** in Railway dashboard

### Update Code
Just push to GitHub:
```bash
git add .
git commit -m "Update"
git push
```
Railway auto-deploys! 🎉

## 💰 Pricing

**Free Tier:**
- 500 hours/month (enough for always-on)
- $5 credit/month
- No credit card needed

**Always-On ($5/month):**
- Never sleeps
- Better performance
- Worth it for production

## 🚨 Troubleshooting

### Service won't start?
- Check **Deployments** → **Logs** for errors
- Verify all environment variables are set
- Check start command: `python enhanced_scheduler.py`

### Not receiving texts?
- Verify Twilio credentials in **Variables**
- Check phone number format: `+1234567890`
- Check Railway logs for Twilio errors

### Want to test first?
- Set `SEND_PICKS_ON_STARTUP=true` temporarily
- Check logs to see first picks

## 📱 Next Steps

1. ✅ Deploy to Railway
2. ✅ Add environment variables
3. ✅ Start receiving picks hourly!
4. 🎯 Monitor logs for first hour
5. 🎉 Enjoy your 24/7 picks!

**That's it! Your system is now running in the cloud!** 🚀

