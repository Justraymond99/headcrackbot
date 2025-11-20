"""Scheduler for hourly picks texting."""
import time
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from hourly_picks import HourlyPicksGenerator
from config import DEFAULT_SPORTS
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def send_picks_job():
    """Job function to send hourly picks."""
    logger.info("="*80)
    logger.info(f"Running hourly picks job at {datetime.now()}")
    logger.info("="*80)
    
    try:
        generator = HourlyPicksGenerator()
        
        # Get configuration from environment or use defaults
        min_ev = float(os.getenv("PICKS_MIN_EV", "0.05"))
        min_confidence = float(os.getenv("PICKS_MIN_CONFIDENCE", "0.6"))
        max_picks = int(os.getenv("PICKS_MAX_COUNT", "5"))
        
        # Get sports from environment or use defaults
        sports_env = os.getenv("PICKS_SPORTS", "")
        if sports_env:
            sports = [s.strip() for s in sports_env.split(",")]
        else:
            sports = DEFAULT_SPORTS
        
        logger.info(f"Configuration: min_ev={min_ev}, min_confidence={min_confidence}, max_picks={max_picks}")
        logger.info(f"Sports: {', '.join(sports)}")
        
        success = generator.send_hourly_picks(
            min_ev=min_ev,
            min_confidence=min_confidence,
            max_picks=max_picks,
            sports=sports,
            refresh_odds=True
        )
        
        if success:
            logger.info("✅ Hourly picks sent successfully")
        else:
            logger.warning("⚠️ Failed to send hourly picks")
    
    except Exception as e:
        logger.error(f"❌ Error in hourly picks job: {e}", exc_info=True)


def main():
    """Main scheduler function."""
    logger.info("Starting hourly picks scheduler...")
    logger.info("Picks will be sent every hour")
    
    # Create scheduler
    scheduler = BlockingScheduler()
    
    # Schedule job to run every hour at minute 0
    scheduler.add_job(
        send_picks_job,
        trigger=CronTrigger(minute=0),  # Run at the top of every hour
        id='hourly_picks',
        name='Send hourly picks via SMS',
        replace_existing=True
    )
    
    # Optional: Send picks immediately on startup
    send_immediately = os.getenv("SEND_PICKS_ON_STARTUP", "false").lower() == "true"
    if send_immediately:
        logger.info("Sending picks immediately on startup...")
        send_picks_job()
    
    try:
        logger.info("Scheduler started. Press Ctrl+C to exit.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()

