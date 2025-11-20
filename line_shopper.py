"""Line shopping - compare odds across multiple sportsbooks."""
from typing import List, Dict, Optional
from datetime import datetime
from models import Game, OddsComparison, Leg, SessionLocal
from data_intake import DataIntake
import logging

logger = logging.getLogger(__name__)


class LineShopper:
    """Compare odds across different sportsbooks."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.data_intake = DataIntake()
        self.bookmakers = ["draftkings", "fanduel", "betmgm", "caesars", "pointsbet"]
    
    def compare_odds(self, game: Game, bet_type: str, selection: str) -> List[Dict]:
        """Compare odds for a specific bet across books."""
        comparisons = []
        
        # Get odds from different books (in real implementation, would fetch from API)
        # For now, simulate with slight variations
        base_odds = self._get_base_odds(game, bet_type, selection)
        
        if base_odds is None:
            return comparisons
        
        for book in self.bookmakers:
            # Simulate odds variation (in real app, fetch from each book's API)
            variation = self._get_book_variation(book)
            odds = base_odds + variation
            
            implied_prob = self._american_to_implied_prob(odds)
            
            comparisons.append({
                "bookmaker": book.title(),
                "odds": odds,
                "implied_probability": implied_prob,
                "edge_vs_average": 0.0  # Will calculate after
            })
        
        # Calculate average and edges
        avg_odds = sum(c["odds"] for c in comparisons) / len(comparisons)
        best_odds = max(comparisons, key=lambda x: x["odds"])
        
        for comp in comparisons:
            comp["edge_vs_average"] = comp["odds"] - avg_odds
            comp["is_best"] = comp == best_odds
        
        return comparisons
    
    def _get_base_odds(self, game: Game, bet_type: str, selection: str) -> Optional[float]:
        """Get base odds for a bet."""
        if bet_type == "moneyline":
            if selection == game.home_team or selection == game.fighter1:
                return game.home_moneyline
            elif selection == game.away_team or selection == game.fighter2:
                return game.away_moneyline
        elif bet_type == "spread":
            if "home" in selection.lower() or game.home_team in selection:
                return game.spread_home_odds
            else:
                return game.spread_away_odds
        elif bet_type == "total":
            if "over" in selection.lower():
                return game.over_odds
            else:
                return game.under_odds
        return None
    
    def _get_book_variation(self, book: str) -> float:
        """Get odds variation for a book (simulated)."""
        variations = {
            "draftkings": 0,
            "fanduel": 5,
            "betmgm": -5,
            "caesars": 3,
            "pointsbet": -3
        }
        return variations.get(book.lower(), 0)
    
    def _american_to_implied_prob(self, american_odds: float) -> float:
        """Convert American odds to implied probability."""
        if american_odds > 0:
            return 100 / (american_odds + 100)
        else:
            return abs(american_odds) / (abs(american_odds) + 100)
    
    def find_best_odds(self, game: Game, bet_type: str, selection: str) -> Dict:
        """Find best available odds for a bet."""
        comparisons = self.compare_odds(game, bet_type, selection)
        if not comparisons:
            return {}
        
        best = max(comparisons, key=lambda x: x["odds"])
        return {
            "bookmaker": best["bookmaker"],
            "odds": best["odds"],
            "implied_probability": best["implied_probability"],
            "edge_vs_average": best["edge_vs_average"],
            "all_books": comparisons
        }
    
    def save_comparison(self, game: Game, leg: Optional[Leg], bet_type: str, selection: str, comparisons: List[Dict]):
        """Save odds comparison to database."""
        # Clear old comparisons
        query = self.session.query(OddsComparison).filter_by(
            game_id=game.id,
            bet_type=bet_type,
            selection=selection
        )
        if leg:
            query = query.filter_by(leg_id=leg.id)
        query.delete()
        
        # Save new comparisons
        for comp in comparisons:
            odds_comp = OddsComparison(
                game_id=game.id,
                leg_id=leg.id if leg else None,
                bet_type=bet_type,
                selection=selection,
                bookmaker=comp["bookmaker"],
                odds=comp["odds"],
                implied_prob=comp["implied_probability"],
                is_best_odds=comp.get("is_best", False),
                edge_vs_average=comp["edge_vs_average"]
            )
            self.session.add(odds_comp)
        
        self.session.commit()
    
    def get_comparison(self, game: Game, bet_type: str, selection: str) -> List[OddsComparison]:
        """Get saved odds comparison."""
        return self.session.query(OddsComparison).filter_by(
            game_id=game.id,
            bet_type=bet_type,
            selection=selection
        ).order_by(OddsComparison.odds.desc()).all()
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

