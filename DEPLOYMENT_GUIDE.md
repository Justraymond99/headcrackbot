# 24/7 Deployment Guide

## 🚀 Quick Start Options

### **Easiest: Railway.app** (Recommended)
- ✅ Free tier available
- ✅ Auto-deploy from GitHub
- ✅ Environment variables GUI
- ✅ Zero configuration needed
- ⚡ Setup time: 5 minutes

### **Also Easy: Render.com**
- ✅ Free tier available
- ✅ Auto-deploy from GitHub
- ✅ Environment variables GUI
- ⚡ Setup time: 10 minutes

### **Cheap & Reliable: DigitalOcean**
- ✅ $5/month droplet
- ✅ Full control
- ✅ Highly reliable
- ⚡ Setup time: 20 minutes

### **Beginner-Friendly: PythonAnywhere**
- ✅ Free tier available
- ✅ Web-based console
- ✅ No command line needed
- ⚡ Setup time: 15 minutes

---

## 🎯 Option 1: Railway.app (EASIEST)

### Steps:

1. **Push your code to GitHub** (if not already)
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Sign up at [railway.app](https://railway.app)**

3. **Create new project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

4. **Configure environment variables**
   - Go to Variables tab
   - Add all your API keys:
     ```
     ODDS_API_KEY=your_key
     SPORTSDATA_API_KEY=your_key
     TWILIO_ACCOUNT_SID=your_sid
     TWILIO_AUTH_TOKEN=your_token
     TWILIO_PHONE_NUMBER=your_number
     USER_PHONE_NUMBER=your_number
     DATABASE_URL=postgresql://...
     ```

5. **Set start command** (in Settings)
   ```
   python enhanced_scheduler.py
   ```

6. **Deploy!** It auto-deploys on push.

**Cost:** Free tier includes 500 hours/month

---

## 🎯 Option 2: Render.com

### Steps:

1. **Push code to GitHub** (same as Railway)

2. **Sign up at [render.com](https://render.com)**

3. **Create new Web Service**
   - New → Web Service
   - Connect GitHub repo
   - Select your repo

4. **Configure:**
   - **Name:** hourly-picks-scheduler
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python enhanced_scheduler.py`

5. **Add Environment Variables** (same as Railway)

6. **Deploy!**

**Cost:** Free tier (spins down after 15min inactivity - upgrade for always-on)

---

## 🎯 Option 3: DigitalOcean Droplet ($5/month)

### Steps:

1. **Create Droplet**
   - Sign up at [digitalocean.com](https://digitalocean.com)
   - Create → Droplet
   - Choose: Ubuntu 22.04
   - Basic plan: $5/month
   - Add your SSH key

2. **SSH into server**
   ```bash
   ssh root@YOUR_IP_ADDRESS
   ```

3. **Install dependencies**
   ```bash
   apt update
   apt install -y python3 python3-pip git postgresql postgresql-contrib
   ```

4. **Clone your repo**
   ```bash
   cd /opt
   git clone YOUR_GITHUB_REPO_URL hourly-picks
   cd hourly-picks
   pip3 install -r requirements.txt
   ```

5. **Set up environment variables**
   ```bash
   nano /opt/hourly-picks/.env
   ```
   Add all your API keys (see example below)

6. **Create systemd service**
   ```bash
   sudo nano /etc/systemd/system/hourly-picks.service
   ```
   (See systemd service file in repo)

7. **Start service**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable hourly-picks
   sudo systemctl start hourly-picks
   sudo systemctl status hourly-picks
   ```

**Cost:** $5/month (always-on)

---

## 🎯 Option 4: PythonAnywhere (Beginner-Friendly)

### Steps:

1. **Sign up at [pythonanywhere.com](https://pythonanywhere.com)**

2. **Upload files**
   - Files tab → Upload files
   - Upload all your Python files

3. **Install packages**
   - Open Bash console
   ```bash
   pip3.10 install --user -r requirements.txt
   ```

4. **Set up scheduled task**
   - Tasks tab → Create scheduled task
   - Command: `python3.10 /home/YOUR_USERNAME/hourly-picks/enhanced_scheduler.py`
   - Hourly: Every hour at :00 and :30

5. **Set environment variables**
   - Files tab → Edit `.bashrc`
   - Add:
     ```bash
     export ODDS_API_KEY="your_key"
     export SPORTSDATA_API_KEY="your_key"
     # ... etc
     ```

**Cost:** Free tier (limited CPU time), $5/month for always-on

---

## 📋 Environment Variables Needed

Create a `.env` file or set these in your platform:

```bash
# API Keys
ODDS_API_KEY=your_odds_api_key
SPORTSDATA_API_KEY=your_sportsdata_key

# Twilio (SMS)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=+1234567890
USER_PHONE_NUMBER=+1234567890

# Database
DATABASE_URL=postgresql://user:password@localhost/dbname
# OR SQLite for simple deployments:
# DATABASE_URL=sqlite:///hourly_picks.db

# Sports Configuration
PICKS_SPORTS=NBA,NFL,MLB,NHL,UFC,BOXING
DEFAULT_SPORTS=NBA,NFL,MLB,NHL,UFC,BOXING

# Pick Thresholds
PICKS_MIN_EV=0.05
PICKS_MIN_CONFIDENCE=0.6
PICKS_MAX_COUNT=5

# Parlay Configuration
PARLAYS_MIN_CONFIDENCE=0.5
PARLAYS_MAX_PER_SPORT=1

# Optional Features
ENABLE_PARLAY_SUGGESTIONS=true
ENABLE_PERFORMANCE_TRACKING=true
ENABLE_LINE_MOVEMENT_ALERTS=true
ENABLE_RESULTS_FOLLOWUP=true

# Scheduler Settings
SEND_PICKS_ON_STARTUP=false
```

---

## 🔧 Additional Files Needed

### For Railway/Render:
- ✅ `Procfile` (already created)
- ✅ `runtime.txt` (if needed for Python version)

### For DigitalOcean/Linux:
- ✅ `hourly-picks.service` (systemd service file - already created)

### For all platforms:
- ✅ `requirements.txt` (should already exist)
- ✅ `.env.example` (template - create this)

---

## ✅ Recommended: Railway.app

**Why Railway?**
- ✅ Easiest setup (5 minutes)
- ✅ Free tier (500 hours/month)
- ✅ Auto-deploys on git push
- ✅ Built-in environment variables
- ✅ Logs in dashboard
- ✅ HTTPS included
- ✅ No credit card needed for free tier

**Steps:**
1. Push code to GitHub
2. Connect Railway to GitHub
3. Add environment variables
4. Deploy!

**Upgrade:** $5/month for always-on (doesn't sleep)

---

## 📱 Monitoring

Once deployed, you can:
- ✅ Check logs in your platform dashboard
- ✅ Set up email alerts for errors
- ✅ Monitor SMS delivery
- ✅ Check database for sent picks

---

## 🚨 Troubleshooting

### Service not starting?
- Check logs: `sudo journalctl -u hourly-picks -f` (Linux)
- Check dashboard logs (Railway/Render)

### Not receiving texts?
- Verify Twilio credentials
- Check `USER_PHONE_NUMBER` format (+1234567890)
- Check Twilio console for delivery status

### Database errors?
- Ensure DATABASE_URL is correct
- For SQLite: Ensure write permissions
- For PostgreSQL: Check connection string

### Scheduler not running?
- Verify timezone settings
- Check system clock (should be UTC)
- Verify cron/systemd service is active

---

## 🎉 Quick Start (Railway)

```bash
# 1. Push to GitHub
git add .
git commit -m "Ready for deployment"
git push

# 2. Go to railway.app
# 3. New Project → Deploy from GitHub
# 4. Add environment variables
# 5. Deploy!

# That's it! 🚀
```

Your picks will now run 24/7! 🎯

