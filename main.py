"""Main execution script for the sports betting parlay system."""
import argparse
import sys
from datetime import datetime
from models import init_db
from data_intake import DataIntake
from research_engine import ResearchEngine
from result_tracker import ResultTracker
from config import DEFAULT_SPORTS
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_data(sports):
    """Fetch and store data from APIs."""
    logger.info("Starting data intake...")
    intake = DataIntake()
    intake.fetch_all_data(sports)
    logger.info("Data intake complete!")


def generate_parlays(sports, max_parlays=10):
    """Generate top parlays."""
    logger.info("Generating parlays...")
    engine = ResearchEngine()
    
    from models import Game, SessionLocal
    session = SessionLocal()
    
    games = session.query(Game).filter(
        Game.sport.in_(sports),
        Game.status == "scheduled"
    ).all()
    
    if not games:
        logger.warning("No games found. Run 'fetch' command first.")
        return
    
    parlays = engine.generate_parlays(games, max_parlays)
    
    if not parlays:
        logger.warning("No qualifying parlays found.")
        return
    
    logger.info(f"Generated {len(parlays)} parlays:")
    print("\n" + "="*80)
    for i, parlay_data in enumerate(parlays, 1):
        print(f"\nParlay {i}: {parlay_data['confidence_rating']} Confidence")
        print(f"  Combined Odds: {parlay_data['combined_odds']:.0f}")
        print(f"  Expected Value: {parlay_data['expected_value']*100:.1f}%")
        print(f"  Implied Probability: {parlay_data['implied_probability']*100:.1f}%")
        print(f"  Score: {parlay_data['score']:.3f}")
        print(f"  Legs ({parlay_data['num_legs']}):")
        for leg in parlay_data['legs']:
            game = leg['game']
            print(f"    - {game.sport}: {game.away_team} @ {game.home_team}")
            print(f"      {leg['bet_type']}: {leg['selection']} @ {leg['odds']:.0f}")
            print(f"      Reasoning: {leg['reasoning']}")
        print("-"*80)
    
    session.close()


def show_performance(days=30):
    """Show performance metrics."""
    logger.info(f"Generating performance report for last {days} days...")
    tracker = ResultTracker()
    trends = tracker.get_performance_trends(days)
    
    if len(trends) == 0:
        logger.info("No performance data available.")
        return
    
    print("\n" + "="*80)
    print("PERFORMANCE REPORT")
    print("="*80)
    print(f"\nAverage ROI: {trends['roi'].mean():.1f}%")
    print(f"Average Hit Rate: {trends['hit_rate'].mean()*100:.1f}%")
    print(f"Total Wins: {trends['wins'].sum()}")
    print(f"Total Losses: {trends['losses'].sum()}")
    print(f"Total Parlays: {trends['total_parlays'].sum()}")
    print("="*80)


def main():
    parser = argparse.ArgumentParser(description="Sports Betting Parlay System")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize database")
    
    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch data from APIs")
    fetch_parser.add_argument(
        "--sports",
        nargs="+",
        default=DEFAULT_SPORTS,
        help="Sports to fetch (default: NBA NFL MLB NHL)"
    )
    
    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate parlays")
    gen_parser.add_argument(
        "--sports",
        nargs="+",
        default=DEFAULT_SPORTS,
        help="Sports to analyze"
    )
    gen_parser.add_argument(
        "--max",
        type=int,
        default=10,
        help="Maximum number of parlays to generate"
    )
    
    # Performance command
    perf_parser = subparsers.add_parser("performance", help="Show performance metrics")
    perf_parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to analyze"
    )
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Launch Streamlit dashboard")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "init":
        init_db()
        print("Database initialized!")
    
    elif args.command == "fetch":
        fetch_data(args.sports)
    
    elif args.command == "generate":
        generate_parlays(args.sports, args.max)
    
    elif args.command == "performance":
        show_performance(args.days)
    
    elif args.command == "dashboard":
        import subprocess
        import os
        dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.py")
        subprocess.run(["streamlit", "run", dashboard_path])


if __name__ == "__main__":
    main()

