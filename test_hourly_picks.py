"""Test script for hourly picks functionality."""
import logging
from hourly_picks import HourlyPicksGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Test sending hourly picks."""
    logger.info("Testing hourly picks generation and SMS...")
    
    try:
        generator = HourlyPicksGenerator()
        
        # Generate and send picks
        success = generator.send_hourly_picks(
            min_ev=0.05,
            min_confidence=0.6,
            max_picks=5,
            refresh_odds=False  # Set to True to refresh odds first
        )
        
        if success:
            logger.info("✅ Test successful! Picks sent.")
        else:
            logger.warning("⚠️ Test completed but SMS may not have been sent (check Twilio config)")
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()

