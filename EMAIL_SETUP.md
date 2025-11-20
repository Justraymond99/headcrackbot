# Email Notification Setup (RECOMMENDED for Personal Use! 🎯)

**MUCH EASIER than SMS!** No registration, no verification, works immediately!

---

## Quick Setup (2 minutes)

### Option 1: Gmail (Easiest)

1. **Enable 2-Factor Authentication** on your Gmail account
   - Go to https://myaccount.google.com/security
   - Enable "2-Step Verification"

2. **Generate an App Password**
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other (Custom name)"
   - Name it "Betting Picks" or whatever
   - Click "Generate"
   - **Copy the 16-character password** (you'll need this!)

3. **Add to your `.env` file:**
   ```env
   # Email Configuration (Gmail)
   EMAIL_ADDRESS=your.email@gmail.com
   EMAIL_PASSWORD=xxxx xxxx xxxx xxxx  # Your App Password (16 chars, spaces don't matter)
   USER_EMAIL=your.email@gmail.com  # Where to send picks (can be same or different)
   
   # Optional: Use different SMTP server (defaults to Gmail)
   # SMTP_SERVER=smtp.gmail.com
   # SMTP_PORT=587
   ```

4. **Test it:**
   ```bash
   python -c "from email_service import EmailService; e = EmailService(); e.send_email('Test', 'It works! 📧')"
   ```

**That's it!** 🎉

---

## Option 2: Other Email Providers

### Outlook/Hotmail
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
EMAIL_ADDRESS=your.email@outlook.com
EMAIL_PASSWORD=your_password_or_app_password
```

### Yahoo
```env
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
EMAIL_ADDRESS=your.email@yahoo.com
EMAIL_PASSWORD=your_app_password  # Generate at https://login.yahoo.com/account/security
```

### Custom SMTP (Your own domain)
```env
SMTP_SERVER=mail.yourdomain.com
SMTP_PORT=587  # or 465 for SSL
EMAIL_ADDRESS=alerts@yourdomain.com
EMAIL_PASSWORD=your_password
```

---

## Why Email is Better for Personal Use

✅ **No registration required** - Just your email credentials  
✅ **Works immediately** - No waiting for approval  
✅ **Free** - No per-message costs  
✅ **More detail** - Can include HTML formatting, more picks  
✅ **Reliable** - Email delivery is very reliable  
✅ **Better formatting** - Tables, colors, etc.

---

## Update Your Code to Use Email

The system is already set up! Just make sure:
1. `EMAIL_ADDRESS`, `EMAIL_PASSWORD`, and `USER_EMAIL` are in your `.env`
2. The scheduler will automatically use email if SMS isn't configured

**Or** update `hourly_picks_enhanced.py` to use `EmailService` instead of `SMSService`:

```python
from email_service import EmailService

# Instead of:
# sms_service = SMSService()
# sms_service.send_picks_sms(picks)

# Use:
email_service = EmailService()
email_service.send_picks_email(picks)
```

---

## Troubleshooting

### "Authentication failed"
- Make sure you're using an **App Password** for Gmail (not your regular password)
- Check that 2FA is enabled
- For other providers, you may need an app-specific password

### "Connection refused"
- Check your firewall isn't blocking port 587
- Try port 465 instead (SSL)

### Emails going to spam
- Add the sender email to your contacts
- Check spam folder
- Consider using a dedicated email address for notifications

---

## Need Help?

- Gmail App Passwords: https://support.google.com/accounts/answer/185833
- Email SMTP Settings: https://www.arclab.com/en/kb/email/list-of-smtp-and-pop3-servers-mailserver-provider.html

