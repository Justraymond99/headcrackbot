"""Advanced filtering system."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Game, Parlay, Leg, SessionLocal
import logging

logger = logging.getLogger(__name__)


class AdvancedFilters:
    """Advanced filtering for games and parlays."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def filter_games(
        self,
        sports: Optional[List[str]] = None,
        date_range: Optional[tuple] = None,
        min_odds: Optional[float] = None,
        max_odds: Optional[float] = None,
        bet_types: Optional[List[str]] = None,
        status: Optional[str] = None
    ) -> List[Game]:
        """Filter games by various criteria."""
        query = self.session.query(Game)
        
        if sports:
            query = query.filter(Game.sport.in_(sports))
        
        if status:
            query = query.filter(Game.status == status)
        else:
            query = query.filter(Game.status == "scheduled")
        
        if date_range:
            start_date, end_date = date_range
            query = query.filter(
                Game.game_date >= start_date,
                Game.game_date <= end_date
            )
        
        games = query.all()
        
        # Filter by odds (post-query filtering)
        if min_odds is not None or max_odds is not None:
            filtered_games = []
            for game in games:
                # Check if game has odds in range
                if game.home_moneyline:
                    if min_odds and game.home_moneyline < min_odds:
                        continue
                    if max_odds and game.home_moneyline > max_odds:
                        continue
                filtered_games.append(game)
            games = filtered_games
        
        return games
    
    def filter_parlays(
        self,
        sports: Optional[List[str]] = None,
        date_range: Optional[tuple] = None,
        min_odds: Optional[float] = None,
        max_odds: Optional[float] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        min_ev: Optional[float] = None,
        status: Optional[str] = None,
        has_props: Optional[bool] = None
    ) -> List[Parlay]:
        """Filter parlays by various criteria."""
        query = self.session.query(Parlay)
        
        if sports:
            query = query.filter(Parlay.sport.in_(sports))
        
        if status:
            query = query.filter(Parlay.status == status)
        
        if date_range:
            start_date, end_date = date_range
            query = query.filter(
                Parlay.created_at >= start_date,
                Parlay.created_at <= end_date
            )
        
        parlays = query.all()
        
        # Post-query filtering
        filtered = []
        for parlay in parlays:
            # Odds filter
            if min_odds and parlay.combined_odds < min_odds:
                continue
            if max_odds and parlay.combined_odds > max_odds:
                continue
            
            # Confidence filter
            if min_confidence and (parlay.confidence_score or 0) < min_confidence:
                continue
            if max_confidence and (parlay.confidence_score or 1) > max_confidence:
                continue
            
            # EV filter
            if min_ev and (parlay.expected_value or 0) < min_ev:
                continue
            
            # Props filter
            if has_props is not None:
                legs = parlay.legs
                has_prop = any(leg.bet_type == "prop" for leg in legs)
                if has_props != has_prop:
                    continue
            
            filtered.append(parlay)
        
        return filtered
    
    def filter_value_bets(
        self,
        min_ev: float = 0.05,
        min_confidence: float = 0.6,
        sports: Optional[List[str]] = None,
        bet_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """Filter value bets."""
        from value_bet_finder import ValueBetFinder
        vf = ValueBetFinder()
        value_bets = vf.find_value_bets(min_ev, min_confidence, sports)
        
        if bet_types:
            value_bets = [vb for vb in value_bets if vb["bet_type"] in bet_types]
        
        return value_bets
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

