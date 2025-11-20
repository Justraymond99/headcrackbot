"""Example usage of the sports betting parlay system."""
from models import init_db
from data_intake import DataIntake
from research_engine import ResearchEngine
from result_tracker import ResultTracker
from config import DEFAULT_SPORTS

def example_workflow():
    """Example workflow demonstrating the system."""
    
    print("="*80)
    print("SPORTS BETTING PARLAY SYSTEM - EXAMPLE WORKFLOW")
    print("="*80)
    
    # Step 1: Initialize database
    print("\n1. Initializing database...")
    init_db()
    print("   ✓ Database initialized")
    
    # Step 2: Fetch data
    print("\n2. Fetching data from APIs...")
    intake = DataIntake()
    intake.fetch_all_data(DEFAULT_SPORTS[:2])  # Just NBA and NFL for example
    print("   ✓ Data fetched and stored")
    
    # Step 3: Generate parlays
    print("\n3. Generating top parlays...")
    engine = ResearchEngine()
    
    from models import Game, SessionLocal
    session = SessionLocal()
    
    games = session.query(Game).filter(
        Game.sport.in_(DEFAULT_SPORTS[:2]),
        Game.status == "scheduled"
    ).all()
    
    if games:
        parlays = engine.generate_parlays(games, max_parlays=5)
        print(f"   ✓ Generated {len(parlays)} parlays")
        
        # Display top parlay
        if parlays:
            top = parlays[0]
            print(f"\n   Top Parlay:")
            print(f"   - Confidence: {top['confidence_rating']}")
            print(f"   - Odds: {top['combined_odds']:.0f}")
            print(f"   - Expected Value: {top['expected_value']*100:.1f}%")
            print(f"   - Legs: {top['num_legs']}")
    else:
        print("   ⚠ No games found (using mock data)")
    
    session.close()
    
    # Step 4: Show performance (if any data exists)
    print("\n4. Performance tracking...")
    tracker = ResultTracker()
    trends = tracker.get_performance_trends(30)
    
    if len(trends) > 0:
        print(f"   ✓ Found {len(trends)} days of performance data")
        print(f"   - Average ROI: {trends['roi'].mean():.1f}%")
        print(f"   - Average Hit Rate: {trends['hit_rate'].mean()*100:.1f}%")
    else:
        print("   ℹ No performance data yet (results will appear after games finish)")
    
    print("\n" + "="*80)
    print("Example workflow complete!")
    print("\nNext steps:")
    print("  - Run 'python main.py dashboard' to use the web interface")
    print("  - Or use 'python main.py generate' to create more parlays")
    print("  - After games finish, update results to track performance")
    print("="*80)


if __name__ == "__main__":
    example_workflow()

