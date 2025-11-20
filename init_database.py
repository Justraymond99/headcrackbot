"""Initialize database with all required tables."""
from models import init_db, Base, engine
from sent_pick import SentPick  # Import to register the table
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Initialize the database."""
    logger.info("Initializing database...")
    
    try:
        # Import all models to ensure they're registered
        from models import (
            Game, PlayerStat, TeamStat, PlayerProp,
            Leg, Parlay, DailyReport, Bankroll
        )
        from sent_pick import SentPick
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        logger.info("✅ Database initialized successfully!")
        logger.info("All tables created:")
        
        # List created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        for table in sorted(tables):
            logger.info(f"   - {table}")
            
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()

