# 🔍 Railway Debug - Nothing Being Sent

## Quick Checks

### 1. Check Railway Logs

Go to Railway → **Deployments** → **View Logs** and look for:

**Good signs:**
- ✅ "Database initialized successfully"
- ✅ "Scheduler started with all features enabled"
- ✅ "Generated X hourly picks"
- ✅ "Telegram message sent successfully"

**Bad signs:**
- ❌ "no such table: games" → Database not initialized
- ❌ "Telegram not configured" → Missing Telegram credentials
- ❌ "Error fetching odds" → API key issues
- ❌ "No picks generated" → No games meet criteria

### 2. Check Environment Variables

In Railway → **Variables** tab, verify:

**Required:**
```
TELEGRAM_BOT_TOKEN=your_new_botfather_token
TELEGRAM_ALLOWED_CHAT_IDS=your_numeric_chat_id
ODDS_API_KEY=your_key
SPORTSDATA_API_KEY=your_key
```

### 3. Check Timing

Picks are sent:
- **Every hour at :00** (e.g., 7:00 PM, 8:00 PM)
- **Every hour at :30** (e.g., 7:30 PM, 8:30 PM)

**If it's not :00 or :30 yet, wait for the next scheduled time!**

### 4. Test Manually

Run this in Railway to test:
```bash
railway run python debug_railway.py
```

Or test locally:
```bash
python3 debug_railway.py
```

### 5. Force Immediate Test

To test immediately, add to Railway Variables:
```
SEND_PICKS_ON_STARTUP=true
```

Then redeploy. This will send picks immediately on startup.

### 6. Check Database

Make sure database is initialized. In Railway logs, look for:
```
INFO:__main__:Initializing database...
INFO:__main__:✅ Database initialized successfully
```

If not, run:
```bash
railway run python init_database.py
```

### 7. Check Telegram

Make sure:
- You've messaged @Justparlaysbot on Telegram
- Telegram credentials are correct in Railway Variables
- Check Telegram for any messages (might be in spam)

---

## Common Issues

### Issue 1: Database Not Initialized
**Solution:** The scheduler should auto-initialize now. Check logs.

### Issue 2: No Games in Database
**Solution:** Games need to be fetched first. The scheduler fetches on startup if `refresh_odds=True`.

### Issue 3: Picks Don't Meet Thresholds
**Solution:** Lower thresholds in Railway Variables:
```
PICKS_MIN_EV=0.01
PICKS_MIN_CONFIDENCE=0.5
```

### Issue 4: Wrong Time
**Solution:** Picks only send at :00 and :30. Wait for next scheduled time.

### Issue 5: Telegram Not Working
**Solution:** 
- Verify bot token and chat ID
- Test with: `railway run python debug_railway.py`
- Make sure you messaged the bot

---

## Quick Fix: Force Send Now

1. Add to Railway Variables:
   ```
   SEND_PICKS_ON_STARTUP=true
   ```

2. Redeploy

3. Check logs - should see picks being sent immediately

4. Remove `SEND_PICKS_ON_STARTUP` after testing (or leave it for immediate sends)

---

## Still Not Working?

Share Railway logs and I can help debug further!

