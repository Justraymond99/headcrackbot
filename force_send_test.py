"""Force send picks test - bypasses all filters."""
import os
from dotenv import load_dotenv
from enhanced_scheduler import send_picks_job
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

if __name__ == "__main__":
    print("=" * 60)
    print("Force Sending Picks Test")
    print("=" * 60)
    print()
    print("This will force send picks immediately...")
    print()
    
    # Set lower thresholds for testing
    os.environ["PICKS_MIN_EV"] = "0.01"
    os.environ["PICKS_MIN_CONFIDENCE"] = "0.5"
    os.environ["PICKS_MAX_COUNT"] = "5"
    
    try:
        send_picks_job()
        print()
        print("✅ Job completed! Check Telegram for picks.")
    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

