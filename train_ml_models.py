"""Script to collect data, update results, and train ML models."""
import logging
from datetime import datetime, timedelta
from models import Game, SessionLocal, init_db
from data_intake import DataIntake
from auto_results import AutoResultUpdater
from ml_models import MLPredictor
from config import DEFAULT_SPORTS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main execution: fetch data, update results, train models."""
    logger.info("="*80)
    logger.info("ML MODEL TRAINING PIPELINE")
    logger.info("="*80)
    
    # Step 1: Initialize database if needed
    logger.info("\n[Step 1/4] Checking database...")
    try:
        init_db()
        logger.info("✅ Database ready")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return
    
    # Step 2: Fetch current games and odds
    logger.info("\n[Step 2/4] Fetching games and odds data...")
    try:
        intake = DataIntake()
        sports = DEFAULT_SPORTS
        # Ensure UFC is included
        if "UFC" not in sports:
            sports = list(sports) + ["UFC"]
        logger.info(f"Fetching data for: {', '.join(sports)}")
        intake.fetch_all_data(sports)
        logger.info("✅ Data fetch complete")
        
        # Check how many games we have
        session = SessionLocal()
        total_games = session.query(Game).count()
        scheduled_games = session.query(Game).filter(Game.status == "scheduled").count()
        finished_games = session.query(Game).filter(Game.status == "finished").count()
        logger.info(f"   Total games in DB: {total_games}")
        logger.info(f"   Scheduled games: {scheduled_games}")
        logger.info(f"   Finished games: {finished_games}")
        session.close()
    except Exception as e:
        logger.error(f"❌ Error fetching data: {e}")
        logger.warning("Continuing with existing data...")
    
    # Step 3: Update results for finished games
    logger.info("\n[Step 3/4] Updating game results...")
    try:
        updater = AutoResultUpdater()
        
        # Update results for past 7 days
        for days_ago in range(7):
            date = datetime.now() - timedelta(days=days_ago)
            for sport in DEFAULT_SPORTS:
                if sport != "UFC":  # UFC results handled differently
                    try:
                        updater.update_results_from_api(sport, date)
                    except Exception as e:
                        logger.debug(f"Could not update {sport} for {date.date()}: {e}")
        
        # Also update all pending results
        updater.update_all_pending_results()
        logger.info("✅ Results update complete")
        
        # Check updated counts
        session = SessionLocal()
        finished_games = session.query(Game).filter(Game.status == "finished").count()
        logger.info(f"   Finished games with results: {finished_games}")
        session.close()
    except Exception as e:
        logger.error(f"❌ Error updating results: {e}")
        logger.warning("Continuing with existing results...")
    
    # Step 4: Train ML models
    logger.info("\n[Step 4/4] Training ML models...")
    try:
        ml_predictor = MLPredictor()
        
        # Check available training data
        logger.info("Checking available training data...")
        ml_data, spread_data, total_data = ml_predictor.prepare_training_data(min_games=1)
        
        data_summary = []
        if ml_data is not None:
            data_summary.append(f"Moneyline: {len(ml_data)} samples")
        else:
            data_summary.append("Moneyline: No data")
        
        if spread_data is not None:
            data_summary.append(f"Spread: {len(spread_data)} samples")
        else:
            data_summary.append("Spread: No data")
        
        if total_data is not None:
            data_summary.append(f"Total: {len(total_data)} samples")
        else:
            data_summary.append("Total: No data")
        
        logger.info(f"   Training data: {', '.join(data_summary)}")
        
        # Train models if we have enough data
        if ml_data is not None and len(ml_data) >= 30:
            logger.info("Training all models...")
            ml_predictor.train_all_models()
            logger.info("✅ ML models trained successfully!")
        else:
            logger.warning("⚠️  Not enough training data (need at least 30 finished games with results)")
            logger.info("   Models will use fallback predictions until more data is available")
            logger.info("   Tip: Update game results manually or wait for more games to finish")
        
        # Check final model status
        logger.info("\nModel Status:")
        if ml_predictor.moneyline_model is not None:
            logger.info("   ✅ Moneyline Model: Trained")
        else:
            logger.info("   ❌ Moneyline Model: Not trained (using fallback)")
        
        if ml_predictor.spread_model is not None:
            logger.info("   ✅ Spread Model: Trained")
        else:
            logger.info("   ❌ Spread Model: Not trained (using fallback)")
        
        if ml_predictor.total_model is not None:
            logger.info("   ✅ Total Model: Trained")
        else:
            logger.info("   ❌ Total Model: Not trained (using fallback)")
        
    except Exception as e:
        logger.error(f"❌ Error training models: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("\n" + "="*80)
    logger.info("PIPELINE COMPLETE")
    logger.info("="*80)
    logger.info("\nNext steps:")
    logger.info("1. Check the dashboard to see your data and models")
    logger.info("2. Generate parlays using the improved ML predictions")
    logger.info("3. Run this script again after more games finish to retrain models")


if __name__ == "__main__":
    main()

