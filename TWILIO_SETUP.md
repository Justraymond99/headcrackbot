# Notification Setup Guide (SMS vs Email)

## ⚠️ Important for Personal Use

For **recreational/personal use** in the US, Twilio requires A2P (Application-to-Person) registration, which can be a hassle. Here are your **easier options**:

---

## Option 1: Email Notifications (RECOMMENDED - No Registration!) 🎯

**Easiest option for personal use!** No registration, no verification, works immediately.

See `EMAIL_SETUP.md` for setup instructions.

---

## Option 2: Twilio SMS (Requires Registration)

If you really want SMS, here's the setup:

### Step 1: Create Twilio Account
1. Go to https://www.twilio.com/try-twilio
2. Sign up for a free account (no credit card required for trial)
3. Verify your email

### Step 2: Get Your Credentials
1. Log into https://www.twilio.com/console
2. Your **Account SID** and **Auth Token** are on the dashboard
3. Copy both - you'll need them for your `.env` file

### Step 3: Register for A2P Messaging (Required for US SMS)

**⚠️ This is required for sending SMS in the US - even for personal use!**

1. Go to **Messaging > Regulatory Compliance > Toll-free & A2P Registration**
2. Click **Register a Brand** (choose "Individual" not "Business")
3. Fill out:
   - **Entity Type**: Individual/Personal
   - Your personal info (name, address, etc.)
   - **Business Type**: Personal/Hobby
   - **Use Case**: Personal notifications/alerts
4. Register a Campaign:
   - **Campaign Use Case**: "Informational Notifications"
   - **Sample Message**: Something like "Your daily betting picks are ready!"
   - **Opt-in**: "Yes, users opt-in via email/signup"
5. Wait for approval (usually 1-3 days, but can take longer)

### Step 4: Get a Phone Number
1. In Twilio Console, go to **Phone Numbers > Buy a number**
2. Click **Buy a number**
3. Select:
   - **Country**: United States
   - **Capabilities**: ✅ SMS
4. Click **Search** and pick any number (~$1/month)
5. Complete the purchase

**You now have:**
- ✅ Twilio Phone Number (e.g., `+15551234567`) - This is your `TWILIO_PHONE_NUMBER`
- ✅ Account SID - This is your `TWILIO_ACCOUNT_SID`
- ✅ Auth Token - This is your `TWILIO_AUTH_TOKEN`

### Step 5: Configure Your .env File

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Twilio credentials:
   ```env
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_PHONE_NUMBER=+15551234567  # Your Twilio number
   USER_PHONE_NUMBER=+19294715507    # Already set! ✅
   ```

### Step 6: Test It!

Run this to test SMS:
```bash
python -c "from sms_service import SMSService; s = SMSService(); s.send_sms('Test message! 📱')"
```

If you see `SMS sent successfully` in the logs, you're good to go! 🎉

---

## Important Notes

### Trial Account Limits
- **Trial accounts**: Can only send SMS to **verified phone numbers**
- To verify your number: Go to Twilio Console > Phone Numbers > Verified Caller IDs
- Add `+19294715507` and verify it (Twilio sends you a code)
- **Or** upgrade to paid ($20 starter credit) to send to any number

### Cost
- **Trial**: Free, but can only text verified numbers
- **Paid**: ~$0.0075 per SMS (less than 1 cent per message!)
- Phone number: ~$1/month

### Why This is Annoying for Personal Use 😤

- **A2P Registration** is required by US carriers (AT&T, Verizon, T-Mobile)
- Even for personal use, you need to register as an "Individual" brand
- Approval can take days or weeks
- Need to provide personal info and use case description

**That's why we recommend Email notifications instead!** 📧

---

## Troubleshooting

### "Error: SMS not configured"
- Make sure your `.env` file exists and has the correct values
- Check that `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_PHONE_NUMBER` are all set

### "Error: Number not verified"
- If on trial account, verify your number in Twilio Console > Verified Caller IDs
- Or upgrade to paid account

### "Error: Invalid phone number"
- Make sure phone numbers are in E.164 format: `+1XXXXXXXXXX`
- Include country code (+1 for US)

---

## Need Help?

- Twilio Docs: https://www.twilio.com/docs/sms
- Twilio Support: https://support.twilio.com/

