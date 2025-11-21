# 🚀 Force Send Picks Immediately (For Testing)

## Quick Fix: Send Picks Right Now

### Step 1: Add Environment Variable

In Railway → **Variables** tab, add:

```
SEND_PICKS_ON_STARTUP=true
```

### Step 2: Redeploy

Railway will automatically redeploy, or manually redeploy:
- Go to Deployments → Click three dots → Redeploy
- Or: `git commit --allow-empty -m "Force send" && git push`

### Step 3: Check Logs

After redeploy, check Railway logs. You should see:
```
INFO:__main__:Sending picks immediately on startup...
INFO:__main__:Generated X hourly picks
INFO:telegram_service:Telegram message sent successfully
```

### Step 4: Check Telegram

You should receive picks immediately!

---

## Why Picks Might Not Be Generating

Based on the debug output, picks aren't being generated because:

1. **No value bets found** - Games don't meet EV/confidence thresholds
2. **No player props** - Games in database don't have prop data
3. **Games are mock data** - API calls might be failing

### Solutions:

**Option 1: Lower Thresholds**

Add to Railway Variables:
```
PICKS_MIN_EV=0.01
PICKS_MIN_CONFIDENCE=0.5
```

**Option 2: Check API Keys**

Make sure `ODDS_API_KEY` is set correctly in Railway Variables.

**Option 3: Check Database**

Make sure games are being fetched. Check Railway logs for:
- "Fetched X games for NBA"
- "Stored X games"

---

## Test Right Now

1. Add `SEND_PICKS_ON_STARTUP=true` to Railway Variables
2. Redeploy
3. Check Telegram immediately
4. Check Railway logs to see what happened

---

## Remove After Testing

Once you confirm it works, you can remove `SEND_PICKS_ON_STARTUP` or leave it for immediate sends on every restart.

