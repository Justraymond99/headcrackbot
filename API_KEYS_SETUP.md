# API Keys & Setup Guide

**Your phone number is already configured: `+19294715507`** ✅

---

## 🎯 RECOMMENDED: Email Notifications (Easiest!)

**For personal/recreational use, email is MUCH easier than SMS!**

### Required:
1. **Gmail App Password** (or any email)
   - See `EMAIL_SETUP.md` for step-by-step guide
   - Takes 2 minutes, no registration needed!

Add to your `.env` file:
```env
EMAIL_ADDRESS=your.email@gmail.com
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx  # Gmail App Password
USER_EMAIL=your.email@gmail.com  # Where to receive picks
```

**That's it!** 📧

---

## Required API Keys

### 1. The Odds API ⚽
- **Where**: https://the-odds-api.com/
- **Free tier**: 500 requests/month
- **What for**: Getting betting odds, lines, props for all sports
- **Add to `.env`:**
  ```env
  ODDS_API_KEY=your_odds_api_key_here
  ```

### 2. SportsData.io 📊
- **Where**: https://sportsdata.io/
- **Free tier**: Limited, but good for testing
- **What for**: Injury reports, player stats, game schedules
- **Add to `.env`:**
  ```env
  SPORTSDATA_API_KEY=your_sportsdata_api_key_here
  ```

---

## Optional: SMS Notifications (Requires Registration)

**⚠️ For personal use, SMS requires A2P registration which can be annoying!**

If you really want SMS:

### Twilio Setup (Requires Registration)
- **Where**: https://www.twilio.com/
- **Cost**: ~$1/month for number + $0.0075 per SMS
- **Registration**: Yes, A2P registration required (can take days/weeks)
- **See**: `TWILIO_SETUP.md` for full instructions

Add to `.env`:
```env
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_PHONE_NUMBER=+15551234567  # Twilio gives you this
USER_PHONE_NUMBER=+19294715507     # Already set! ✅
```

---

## Quick Start

1. **Create `.env` file** in the project root:
   ```bash
   cp .env.example .env  # If .env.example exists
   ```

2. **Add your API keys:**
   ```env
   # Required
   ODDS_API_KEY=your_key_here
   SPORTSDATA_API_KEY=your_key_here
   
   # Email (RECOMMENDED - Easy!)
   EMAIL_ADDRESS=your.email@gmail.com
   EMAIL_PASSWORD=your_app_password
   USER_EMAIL=your.email@gmail.com
   
   # OR SMS (Requires registration)
   # TWILIO_ACCOUNT_SID=...
   # TWILIO_AUTH_TOKEN=...
   # TWILIO_PHONE_NUMBER=...
   # USER_PHONE_NUMBER=+19294715507  # Already set!
   ```

3. **Test it:**
   ```bash
   python -c "from email_service import EmailService; e = EmailService(); e.send_email('Test', 'Setup complete! ✅')"
   ```

---

## Summary

| Method | Difficulty | Registration | Cost |
|--------|-----------|--------------|------|
| **Email** 🎯 | ⭐ Easy | ❌ None | ✅ Free |
| SMS (Twilio) | ⭐⭐⭐ Hard | ✅ Required | 💰 ~$1/month |

**Recommendation**: Use Email for personal use! Much easier! 📧

---

## Need Help?

- Email Setup: See `EMAIL_SETUP.md`
- Twilio Setup: See `TWILIO_SETUP.md`
- API Issues: Check the individual API documentation

