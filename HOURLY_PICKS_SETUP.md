# Hourly Picks Texting Setup Guide

This guide will help you set up hourly picks to be texted to you based on betting odds.

## Prerequisites

1. **Twilio Account**: Sign up at https://www.twilio.com (free trial available)
2. **Python Dependencies**: Install required packages

## Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Twilio**:
   - Sign up for a Twilio account at https://www.twilio.com
   - Get your Account SID and Auth Token from the Twilio Console
   - Get a Twilio phone number (free trial includes one)
   - Verify your phone number in Twilio Console (for trial accounts)

3. **Configure environment variables**:
   
   Add these to your `.env` file:
   ```env
   # Twilio SMS Configuration
   TWILIO_ACCOUNT_SID=your_account_sid_here
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_PHONE_NUMBER=+1234567890  # Your Twilio phone number (format: +1234567890)
   USER_PHONE_NUMBER=+1234567890    # Your phone number to receive texts (format: +1234567890)
   
   # Optional: Customize picks settings
   PICKS_MIN_EV=0.05                # Minimum expected value (default: 0.05)
   PICKS_MIN_CONFIDENCE=0.6         # Minimum confidence (default: 0.6)
   PICKS_MAX_COUNT=5                # Max picks per message (default: 5)
   PICKS_SPORTS=NBA,NFL,MLB,NHL,UFC # Sports to analyze (comma-separated)
   SEND_PICKS_ON_STARTUP=false      # Send picks immediately when scheduler starts
   ```

## Usage

### Start the Hourly Scheduler

Run the scheduler to send picks every hour:

```bash
python scheduler.py
```

The scheduler will:
- Send picks at the top of every hour (e.g., 1:00 PM, 2:00 PM, etc.)
- Refresh odds data before generating picks
- Send the top picks via SMS

### Test Sending Picks (One-Time)

To test sending picks without starting the scheduler:

```python
from hourly_picks import HourlyPicksGenerator

generator = HourlyPicksGenerator()
generator.send_hourly_picks(
    min_ev=0.05,
    min_confidence=0.6,
    max_picks=5,
    refresh_odds=True
)
```

Or create a simple test script:

```python
# test_picks.py
from hourly_picks import HourlyPicksGenerator

if __name__ == "__main__":
    generator = HourlyPicksGenerator()
    generator.send_hourly_picks()
```

Run it:
```bash
python test_picks.py
```

## Running in Background

### Using nohup (Linux/Mac)

```bash
nohup python scheduler.py > scheduler.log 2>&1 &
```

### Using screen (Linux/Mac)

```bash
screen -S picks_scheduler
python scheduler.py
# Press Ctrl+A then D to detach
# Reattach with: screen -r picks_scheduler
```

### Using systemd (Linux)

Create `/etc/systemd/system/hourly-picks.service`:

```ini
[Unit]
Description=Hourly Sports Betting Picks Scheduler
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/tictactoe
ExecStart=/usr/bin/python3 /path/to/tictactoe/scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable hourly-picks
sudo systemctl start hourly-picks
```

## Customization

### Adjust Pick Criteria

Edit your `.env` file:
- `PICKS_MIN_EV`: Higher = more selective (default: 0.05)
- `PICKS_MIN_CONFIDENCE`: Higher = more confident picks (default: 0.6)
- `PICKS_MAX_COUNT`: Number of picks per message (default: 5)

### Change Sports

Set `PICKS_SPORTS` in `.env`:
```env
PICKS_SPORTS=NBA,NFL  # Only NBA and NFL
```

### Change Schedule

Edit `scheduler.py` to change when picks are sent:
```python
# Run every 2 hours
scheduler.add_job(
    send_picks_job,
    trigger=CronTrigger(hour='*/2'),  # Every 2 hours
    ...
)

# Run at specific times
scheduler.add_job(
    send_picks_job,
    trigger=CronTrigger(hour='9,12,15,18'),  # 9 AM, 12 PM, 3 PM, 6 PM
    ...
)
```

## Troubleshooting

### No SMS Received

1. **Check Twilio credentials**: Verify Account SID, Auth Token, and phone numbers in `.env`
2. **Verify phone number**: For trial accounts, your phone number must be verified in Twilio Console
3. **Check logs**: Look for error messages in the console or log files
4. **Test SMS service**: Run a simple test:
   ```python
   from sms_service import SMSService
   sms = SMSService()
   sms.send_sms("Test message")
   ```

### No Picks Generated

1. **Check database**: Make sure you have scheduled games in the database
   ```bash
   python main.py fetch
   ```
2. **Lower thresholds**: Try lowering `PICKS_MIN_EV` and `PICKS_MIN_CONFIDENCE`
3. **Check logs**: Look for warnings about no games found

### Scheduler Not Running

1. **Check Python path**: Make sure you're using the correct Python interpreter
2. **Check dependencies**: Ensure all packages are installed
3. **Check permissions**: Make sure the script has write permissions for logs

## Message Format

Picks are sent in this format:

```
🏀 HOURLY PICKS 🏀

1. NBA: Lakers
   Warriors @ Lakers
   MONEYLINE | +150 | 🔥 78% | EV: +5.2%

2. NFL: Chiefs -3.5
   Chiefs @ Bills
   SPREAD | -110 | 🟢 68% | EV: +3.1%

...

📱 Check dashboard for full details
```

## Notes

- **Twilio Free Trial**: Includes limited credits. Upgrade for production use.
- **API Limits**: Make sure your odds API keys have sufficient requests
- **Database**: Ensure your database is up to date with latest games
- **Timezone**: Scheduler uses system timezone. Adjust CronTrigger if needed.

