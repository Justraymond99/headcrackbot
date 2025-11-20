"""Database models for sports betting data."""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import DATABASE_URL

Base = declarative_base()

class Game(Base):
    """Store game/matchup information."""
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(String, unique=True, nullable=False)
    sport = Column(String, nullable=False)  # NBA, NFL, MLB, NHL, UFC, BOXING
    home_team = Column(String)  # Nullable for UFC
    away_team = Column(String)  # Nullable for UFC
    fighter1 = Column(String)  # For UFC
    fighter2 = Column(String)  # For UFC
    game_date = Column(DateTime, nullable=False)
    status = Column(String)  # scheduled, live, finished
    
    # Odds data
    home_moneyline = Column(Float)
    away_moneyline = Column(Float)
    spread = Column(Float)
    spread_home_odds = Column(Float)
    spread_away_odds = Column(Float)
    total = Column(Float)
    over_odds = Column(Float)
    under_odds = Column(Float)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    legs = relationship("Leg", back_populates="game")
    player_stats = relationship("PlayerStat", back_populates="game")
    player_props = relationship("PlayerProp", back_populates="game")
    
    def __repr__(self):
        if self.sport in ["UFC", "BOXING"]:
            return f"<Game({self.sport}: {self.fighter1} vs {self.fighter2})>"
        return f"<Game({self.sport}: {self.away_team} @ {self.home_team})>"


class PlayerStat(Base):
    """Store player statistics and injury reports."""
    __tablename__ = "player_stats"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_name = Column(String, nullable=False)
    team = Column(String, nullable=False)
    position = Column(String)
    
    # Stats
    points = Column(Float)
    rebounds = Column(Float)
    assists = Column(Float)
    injury_status = Column(String)  # healthy, questionable, doubtful, out
    
    # Advanced stats
    advanced_stats = Column(JSON)  # Store as JSON for flexibility
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    game = relationship("Game", back_populates="player_stats")


class TeamStat(Base):
    """Store team statistics and streaks."""
    __tablename__ = "team_stats"
    
    id = Column(Integer, primary_key=True)
    team = Column(String, nullable=False)
    sport = Column(String, nullable=False)
    season = Column(String)
    
    # Streaks
    win_streak = Column(Integer, default=0)
    loss_streak = Column(Integer, default=0)
    home_record = Column(String)  # "W-L" format
    away_record = Column(String)
    
    # Advanced stats
    offensive_rating = Column(Float)
    defensive_rating = Column(Float)
    pace = Column(Float)
    advanced_stats = Column(JSON)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlayerProp(Base):
    """Store player prop bets for all sports."""
    __tablename__ = "player_props"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_name = Column(String, nullable=False)
    prop_type = Column(String, nullable=False)  # Market key from API (e.g., player_points, player_pass_yds)
    prop_value = Column(Float)  # The line (e.g., 25.5 points) - nullable for Yes/No props
    over_odds = Column(Float)
    under_odds = Column(Float)
    yes_odds = Column(Float)  # For Yes/No props (e.g., anytime TD scorer)
    no_odds = Column(Float)   # For Yes/No props
    
    # Market metadata
    market_key = Column(String)  # Original API market key
    description = Column(String)  # Human-readable description
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    game = relationship("Game", back_populates="player_props")


class Leg(Base):
    """Individual leg of a parlay."""
    __tablename__ = "legs"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    parlay_id = Column(Integer, ForeignKey("parlays.id"), nullable=False)
    player_prop_id = Column(Integer, ForeignKey("player_props.id"), nullable=True)  # For prop bets
    
    # Bet details
    bet_type = Column(String, nullable=False)  # moneyline, spread, total, prop, fighter_moneyline
    selection = Column(String, nullable=False)  # team/fighter name, "over"/"under", or prop description
    odds = Column(Float, nullable=False)
    implied_probability = Column(Float)
    expected_value = Column(Float)
    confidence_score = Column(Float)
    
    # Prop-specific fields
    prop_type = Column(String)  # points, rebounds, assists, etc. (for props)
    prop_value = Column(Float)  # The line value (for props)
    player_name = Column(String)  # Player name (for props)
    
    # Reasoning
    reasoning = Column(Text)
    
    # Result
    result = Column(String)  # win, loss, push, pending
    actual_outcome = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    game = relationship("Game", back_populates="legs")
    parlay = relationship("Parlay", back_populates="legs")
    
    def __repr__(self):
        if self.bet_type == "prop":
            return f"<Leg({self.bet_type}: {self.player_name} {self.prop_type} {self.selection} {self.prop_value} @ {self.odds})>"
        return f"<Leg({self.bet_type}: {self.selection} @ {self.odds})>"


class Parlay(Base):
    """Parlay bet containing multiple legs."""
    __tablename__ = "parlays"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    sport = Column(String)
    
    # Parlay details
    combined_odds = Column(Float, nullable=False)
    implied_probability = Column(Float)
    expected_value = Column(Float)
    confidence_rating = Column(String)  # High, Moderate, Low
    confidence_score = Column(Float)  # 0-1
    
    # Status
    status = Column(String, default="pending")  # pending, locked, won, lost
    locked = Column(Boolean, default=False)
    locked_at = Column(DateTime)
    
    # Result tracking
    result = Column(String)  # win, loss, pending
    payout = Column(Float)
    stake = Column(Float, default=1.0)  # Default $1 unit
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    legs = relationship("Leg", back_populates="parlay", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Parlay({self.name}: {self.combined_odds} odds, {self.confidence_rating})>"


class DailyReport(Base):
    """Daily summary reports."""
    __tablename__ = "daily_reports"
    
    id = Column(Integer, primary_key=True)
    report_date = Column(DateTime, nullable=False, unique=True)
    
    # Summary stats
    total_parlays = Column(Integer, default=0)
    locked_parlays = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    hit_rate = Column(Float)
    roi = Column(Float)
    total_stake = Column(Float)
    total_payout = Column(Float)
    
    # Export status
    exported_to_notion = Column(Boolean, default=False)
    exported_to_sheets = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class Bankroll(Base):
    """Bankroll management and tracking."""
    __tablename__ = "bankroll"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, default="default")  # For multi-user support
    
    # Bankroll info
    current_balance = Column(Float, default=1000.0)
    starting_balance = Column(Float, default=1000.0)
    total_deposits = Column(Float, default=0.0)
    total_withdrawals = Column(Float, default=0.0)
    
    # Limits
    daily_budget = Column(Float)
    weekly_budget = Column(Float)
    monthly_budget = Column(Float)
    max_bet_size = Column(Float)
    max_parlay_stake = Column(Float)
    
    # Unit sizing
    base_unit_size = Column(Float, default=1.0)  # 1% of bankroll
    kelly_fraction = Column(Float, default=0.25)  # Fractional Kelly
    
    # Tracking
    daily_stake = Column(Float, default=0.0)
    weekly_stake = Column(Float, default=0.0)
    monthly_stake = Column(Float, default=0.0)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class OddsComparison(Base):
    """Line shopping - compare odds across books."""
    __tablename__ = "odds_comparisons"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    leg_id = Column(Integer, ForeignKey("legs.id"), nullable=True)
    
    # Bet details
    bet_type = Column(String, nullable=False)
    selection = Column(String, nullable=False)
    
    # Odds from different books
    bookmaker = Column(String, nullable=False)  # DraftKings, FanDuel, etc.
    odds = Column(Float, nullable=False)
    implied_prob = Column(Float)
    
    # Best odds tracking
    is_best_odds = Column(Boolean, default=False)
    edge_vs_average = Column(Float)  # Edge vs average odds
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    game = relationship("Game")


class ValueBet(Base):
    """Value bet finder results."""
    __tablename__ = "value_bets"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    
    # Bet details
    bet_type = Column(String, nullable=False)
    selection = Column(String, nullable=False)
    odds = Column(Float, nullable=False)
    
    # Value metrics
    implied_probability = Column(Float)
    true_probability = Column(Float)
    expected_value = Column(Float)
    edge_percentage = Column(Float)  # EV as percentage
    value_score = Column(Float)  # Combined score
    
    # Confidence
    confidence_level = Column(String)  # High, Medium, Low
    confidence_score = Column(Float)
    
    # Status
    status = Column(String, default="available")  # available, locked, expired
    locked_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    game = relationship("Game")


class ClosingLineValue(Base):
    """Closing Line Value tracking."""
    __tablename__ = "closing_line_value"
    
    id = Column(Integer, primary_key=True)
    leg_id = Column(Integer, ForeignKey("legs.id"), nullable=False)
    
    # Odds comparison
    opening_odds = Column(Float)
    your_odds = Column(Float)  # Odds you got
    closing_odds = Column(Float)
    
    # CLV metrics
    clv_percentage = Column(Float)  # (closing - your) / your
    beat_closing_line = Column(Boolean)  # Did you beat closing?
    sharp_indicator = Column(Float)  # 0-1 score
    
    # Line movement
    line_movement = Column(Float)  # Change in odds
    movement_direction = Column(String)  # toward_you, away_from_you
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    leg = relationship("Leg")


class Streak(Base):
    """Win/loss streak tracking."""
    __tablename__ = "streaks"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, default="default")
    
    # Streak info
    streak_type = Column(String, nullable=False)  # win, loss
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    
    # Context
    sport = Column(String)  # Optional: filter by sport
    bet_type = Column(String)  # Optional: filter by bet type
    
    # Dates
    streak_started = Column(DateTime)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    """Notifications and alerts."""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, default="default")
    
    # Notification details
    notification_type = Column(String, nullable=False)  # odds_alert, result, line_movement, etc.
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    # Status
    read = Column(Boolean, default=False)
    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    
    # Priority
    priority = Column(String, default="normal")  # low, normal, high, urgent
    
    # Related entities
    related_game_id = Column(Integer, ForeignKey("games.id"), nullable=True)
    related_parlay_id = Column(Integer, ForeignKey("parlays.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    game = relationship("Game")
    parlay = relationship("Parlay")


class BetSlip(Base):
    """Bet slip builder."""
    __tablename__ = "bet_slips"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, default="default")
    name = Column(String)
    
    # Slip details
    legs = Column(JSON)  # Store leg data as JSON
    total_odds = Column(Float)
    stake = Column(Float)
    potential_payout = Column(Float)
    
    # Status
    status = Column(String, default="draft")  # draft, saved, placed
    saved = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HistoricalMatchup(Base):
    """Historical matchup data."""
    __tablename__ = "historical_matchups"
    
    id = Column(Integer, primary_key=True)
    
    # Teams/Fighters
    team1 = Column(String, nullable=False)
    team2 = Column(String, nullable=False)
    sport = Column(String, nullable=False)
    
    # Head-to-head
    team1_wins = Column(Integer, default=0)
    team2_wins = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    
    # Recent meetings
    last_5_games = Column(JSON)  # Store last 5 results
    avg_total = Column(Float)
    avg_margin = Column(Float)
    
    # Trends
    team1_home_record = Column(String)
    team2_away_record = Column(String)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class MarketEfficiency(Base):
    """Market efficiency tracking."""
    __tablename__ = "market_efficiency"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    
    # Line movement
    opening_line = Column(Float)
    current_line = Column(Float)
    closing_line = Column(Float)
    line_movement = Column(Float)
    
    # Public vs sharp
    public_percentage = Column(Float)  # % of public on one side
    sharp_percentage = Column(Float)  # % of sharp money
    reverse_line_movement = Column(Boolean)  # Line moves opposite of public
    
    # Steam moves
    steam_move_detected = Column(Boolean, default=False)
    steam_move_time = Column(DateTime, nullable=True)
    
    # Efficiency score
    efficiency_score = Column(Float)  # 0-1, higher = more efficient
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    game = relationship("Game")


class CustomStat(Base):
    """User-defined custom statistics."""
    __tablename__ = "custom_stats"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, default="default")
    
    # Stat definition
    name = Column(String, nullable=False)
    description = Column(Text)
    formula = Column(Text, nullable=False)  # Python expression or SQL
    
    # Scope
    sport = Column(String)  # Optional filter
    stat_type = Column(String)  # team, player, game
    
    # Results cache
    last_calculated = Column(DateTime)
    values = Column(JSON)  # Store calculated values
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SocialParlay(Base):
    """Social features - shared parlays."""
    __tablename__ = "social_parlays"
    
    id = Column(Integer, primary_key=True)
    parlay_id = Column(Integer, ForeignKey("parlays.id"), nullable=False)
    user_id = Column(String, default="default")
    
    # Social features
    public = Column(Boolean, default=False)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    copied = Column(Integer, default=0)
    
    # Tags
    tags = Column(JSON)  # Array of tags
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    parlay = relationship("Parlay")


class UserFollow(Base):
    """User following system."""
    __tablename__ = "user_follows"
    
    id = Column(Integer, primary_key=True)
    follower_id = Column(String, nullable=False)
    following_id = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Unique constraint
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


# Database setup
# Use SQLite if DATABASE_URL is not set or is invalid
if not DATABASE_URL or (DATABASE_URL.startswith("postgresql") and "schema" in DATABASE_URL):
    DATABASE_URL = "sqlite:///./sports_betting.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Initialize the database with all tables."""
    # Import sent_pick to ensure its table is registered
    try:
        from sent_pick import SentPick
    except ImportError:
        pass
    
    Base.metadata.create_all(engine)
    print("Database initialized successfully!")

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

