# 🔍 Railway Troubleshooting - No Picks Generated

## Common Issues & Solutions

### 1. Check Railway Logs for Errors

Go to Railway → **Deployments** → **View Logs** and look for:
- ❌ Error messages
- ⚠️ Warning messages
- Database errors
- API errors

### 2. Verify Environment Variables

In Railway → **Variables** tab, make sure these are set:

**Required:**
```
TELEGRAM_BOT_TOKEN=8506045290:AAGm8d-kYJoBOtgwsNJalE_kZicAgDPFZXs
TELEGRAM_CHAT_ID=7197338861
ODDS_API_KEY=your_key_here
SPORTSDATA_API_KEY=your_key_here
```

**If missing:**
- Picks won't be generated (no API access)
- Or picks won't be sent (no Telegram)

### 3. Check Database Initialization

The database needs to be initialized. Check logs for:
```
INFO:__main__:Database initialized successfully!
```

**If not initialized:**
- Run: `railway run python init_database.py`
- Or check if there are database errors in logs

### 4. Check if Games Exist

The scheduler needs scheduled games in the database to generate picks.

**Possible reasons for no picks:**
- No games in database (need to fetch odds first)
- Games are too far in the future
- Games don't meet EV/confidence thresholds
- API keys not working (check API limits)

### 5. Test Manually

Run this in Railway to test:
```bash
railway run python test_picks_generation.py
```

Or locally:
```bash
python3 test_picks_generation.py
```

### 6. Check Scheduler Timing

Picks are sent:
- Every hour at :00 (e.g., 7:00 PM, 8:00 PM)
- Every hour at :30 (e.g., 7:30 PM, 8:30 PM)

**If it's not :00 or :30 yet, wait for the next scheduled time.**

### 7. Force Immediate Test

To test immediately, set in Railway Variables:
```
SEND_PICKS_ON_STARTUP=true
```

Then redeploy. This will send picks immediately on startup.

### 8. Check API Keys

**ODDS_API_KEY:**
- Verify it's valid
- Check if you've hit API limits
- Test: `curl "https://api.the-odds-api.com/v4/sports?apiKey=YOUR_KEY"`

**SPORTSDATA_API_KEY:**
- Verify it's valid
- Check subscription status

### 9. Database Issues

If you see database errors:
```bash
railway run python init_database.py
```

Check if tables exist:
```bash
railway run python -c "from models import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"
```

### 10. Check Logs for Specific Errors

Look for these in Railway logs:
- `No scheduled games found` → Need to fetch odds
- `Telegram not configured` → Missing Telegram credentials
- `Error fetching odds` → API key issue
- `Database error` → Database not initialized

---

## Quick Fixes

**If nothing is working:**

1. **Check all environment variables are set**
2. **Initialize database:**
   ```bash
   railway run python init_database.py
   ```
3. **Test manually:**
   ```bash
   railway run python test_picks_generation.py
   ```
4. **Check Railway logs for errors**
5. **Verify API keys are valid**

---

## Still Not Working?

Share the Railway logs and I can help debug further!

