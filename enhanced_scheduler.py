"""Enhanced scheduler with all new features."""
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from hourly_picks_enhanced import EnhancedHourlyPicksGenerator
from pick_enhancements import PickEnhancements
from config import DEFAULT_SPORTS
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Optional WebSocket server
try:
    from websocket_integration import start_websocket_background
    from websocket_server import broadcast_system_message
    WEBSOCKET_ENABLED = os.getenv("ENABLE_WEBSOCKET", "false").lower() == "true"
    WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", "5000"))
except ImportError:
    WEBSOCKET_ENABLED = False
    logger.debug("WebSocket not available (optional feature)")


def send_picks_job():
    """Main hourly picks job - sends individual picks."""
    logger.info("="*80)
    logger.info(f"Running hourly picks job at {datetime.now()}")
    logger.info("="*80)
    
    try:
        generator = EnhancedHourlyPicksGenerator()
        
        min_ev = float(os.getenv("PICKS_MIN_EV", "0.05"))
        min_confidence = float(os.getenv("PICKS_MIN_CONFIDENCE", "0.6"))
        max_picks = int(os.getenv("PICKS_MAX_COUNT", "5"))
        
        sports_env = os.getenv("PICKS_SPORTS", "")
        if sports_env:
            sports = [s.strip() for s in sports_env.split(",")]
        else:
            sports = DEFAULT_SPORTS
        
        success = generator.send_hourly_picks(
            min_ev=min_ev,
            min_confidence=min_confidence,
            max_picks=max_picks,
            sports=sports,
            refresh_odds=True
        )
        
        if success:
            logger.info("✅ Hourly picks sent successfully")
            # Broadcast via WebSocket if enabled
            if WEBSOCKET_ENABLED:
                try:
                    broadcast_system_message("Hourly picks sent successfully", "success")
                except:
                    pass
        else:
            logger.warning("⚠️ Failed to send hourly picks")
    
    except Exception as e:
        logger.error(f"❌ Error in hourly picks job: {e}", exc_info=True)


def send_parlays_job():
    """Hourly parlay picks job - sends best parlay from each sport."""
    logger.info("="*80)
    logger.info(f"Running hourly parlays job at {datetime.now()}")
    logger.info("="*80)
    
    try:
        generator = EnhancedHourlyPicksGenerator()
        
        min_confidence = float(os.getenv("PARLAYS_MIN_CONFIDENCE", "0.5"))
        max_parlays_per_sport = int(os.getenv("PARLAYS_MAX_PER_SPORT", "1"))
        
        sports_env = os.getenv("PICKS_SPORTS", "")
        if sports_env:
            sports = [s.strip() for s in sports_env.split(",")]
        else:
            sports = DEFAULT_SPORTS
        
        success = generator.send_diverse_parlays_hourly(
            sports=sports,
            min_confidence=min_confidence,
            max_parlays_per_sport=max_parlays_per_sport,
            refresh_odds=True
        )
        
        if success:
            logger.info("✅ Hourly parlays sent successfully")
            # Broadcast via WebSocket if enabled
            if WEBSOCKET_ENABLED:
                try:
                    broadcast_system_message("Hourly parlays sent successfully", "success")
                except:
                    pass
        else:
            logger.warning("⚠️ Failed to send hourly parlays")
    
    except Exception as e:
        logger.error(f"❌ Error in hourly parlays job: {e}", exc_info=True)


def send_parlay_suggestions_job():
    """Send parlay suggestions (runs once per day)."""
    if os.getenv("ENABLE_PARLAY_SUGGESTIONS", "false").lower() != "true":
        return
    
    logger.info("Sending parlay suggestions...")
    try:
        enhancer = PickEnhancements()
        enhancer.send_parlay_suggestions(max_parlays=2)
        logger.info("✅ Parlay suggestions sent")
    except Exception as e:
        logger.error(f"❌ Error sending parlay suggestions: {e}", exc_info=True)


def send_performance_summary_job():
    """Send daily performance summary."""
    if os.getenv("ENABLE_PERFORMANCE_TRACKING", "false").lower() != "true":
        return
    
    logger.info("Sending performance summary...")
    try:
        enhancer = PickEnhancements()
        days = int(os.getenv("PERFORMANCE_SUMMARY_DAYS", "7"))
        enhancer.send_performance_summary(days=days, include_sport_breakdown=True)
        logger.info("✅ Performance summary sent")
    except Exception as e:
        logger.error(f"❌ Error sending performance summary: {e}", exc_info=True)


def check_line_movements_job():
    """Check for favorable line movements."""
    if os.getenv("ENABLE_LINE_MOVEMENT_ALERTS", "false").lower() != "true":
        return
    
    logger.info("Checking for line movements...")
    try:
        enhancer = PickEnhancements()
        min_improvement = float(os.getenv("LINE_MOVEMENT_MIN_IMPROVEMENT", "10.0"))
        hours = int(os.getenv("LINE_MOVEMENT_CHECK_HOURS", "6"))
        enhancer.send_line_movement_alerts(min_improvement=min_improvement, hours=hours)
        logger.info("✅ Line movement check complete")
    except Exception as e:
        logger.error(f"❌ Error checking line movements: {e}", exc_info=True)


def send_results_followup_job():
    """Send pick results for finished games."""
    if os.getenv("ENABLE_RESULTS_FOLLOWUP", "false").lower() != "true":
        return
    
    logger.info("Sending pick results follow-up...")
    try:
        enhancer = PickEnhancements()
        hours = int(os.getenv("RESULTS_FOLLOWUP_HOURS", "24"))
        enhancer.send_pick_results_followup(hours=hours)
        logger.info("✅ Results follow-up sent")
    except Exception as e:
        logger.error(f"❌ Error sending results follow-up: {e}", exc_info=True)


def main():
    """Main scheduler function with all features."""
    logger.info("Starting enhanced hourly picks scheduler...")
    
    # Initialize database if needed
    try:
        from models import init_db
        logger.info("Initializing database...")
        init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization check failed: {e}")
        # Try to continue anyway - database might already exist
    
    # Start WebSocket server if enabled
    if WEBSOCKET_ENABLED:
        try:
            start_websocket_background(port=WEBSOCKET_PORT)
            broadcast_system_message("Hourly Picks Scheduler started", "info")
            logger.info(f"✅ WebSocket server started on port {WEBSOCKET_PORT}")
        except Exception as e:
            logger.warning(f"Failed to start WebSocket server: {e}")
    
    scheduler = BlockingScheduler()
    
    # Main hourly picks (every hour at :00)
    scheduler.add_job(
        send_picks_job,
        trigger=CronTrigger(minute=0),
        id='hourly_picks',
        name='Send hourly picks',
        replace_existing=True
    )
    
    # Hourly parlay picks - best parlay from each sport (every hour at :30)
    scheduler.add_job(
        send_parlays_job,
        trigger=CronTrigger(minute=30),
        id='hourly_parlays',
        name='Send hourly parlays (each sport)',
        replace_existing=True
    )
    
    # Parlay suggestions (daily at 10 AM)
    parlay_hour = int(os.getenv("PARLAY_SUGGESTIONS_TIME", "10"))
    scheduler.add_job(
        send_parlay_suggestions_job,
        trigger=CronTrigger(hour=parlay_hour, minute=0),
        id='parlay_suggestions',
        name='Send parlay suggestions',
        replace_existing=True
    )
    
    # Performance summary (daily at 9 PM)
    scheduler.add_job(
        send_performance_summary_job,
        trigger=CronTrigger(hour=21, minute=0),
        id='performance_summary',
        name='Send performance summary',
        replace_existing=True
    )
    
    # Line movement checks (every 2 hours)
    scheduler.add_job(
        check_line_movements_job,
        trigger=CronTrigger(hour='*/2', minute=0),
        id='line_movements',
        name='Check line movements',
        replace_existing=True
    )
    
    # Results follow-up (every 4 hours)
    scheduler.add_job(
        send_results_followup_job,
        trigger=CronTrigger(hour='*/4', minute=0),
        id='results_followup',
        name='Send pick results',
        replace_existing=True
    )
    
    # Optional: Send picks immediately on startup
    send_immediately = os.getenv("SEND_PICKS_ON_STARTUP", "false").lower() == "true"
    if send_immediately:
        logger.info("Sending picks immediately on startup...")
        try:
            send_picks_job()
        except Exception as e:
            logger.error(f"Error sending picks on startup: {e}", exc_info=True)
    
    # Also send parlays immediately if requested
    send_parlays_immediately = os.getenv("SEND_PARLAYS_ON_STARTUP", "false").lower() == "true"
    if send_parlays_immediately:
        logger.info("Sending parlays immediately on startup...")
        try:
            send_parlays_job()
        except Exception as e:
            logger.error(f"Error sending parlays on startup: {e}", exc_info=True)
    
    try:
        logger.info("Scheduler started with all features enabled.")
        logger.info("Press Ctrl+C to exit.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()

