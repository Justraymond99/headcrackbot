"""Picks Dashboard - Visual pick cards with confidence, line movement, and AI analysis."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Game, Leg, Parlay, PlayerProp, SessionLocal
from ai_picks import AIPicks
from research_engine import ResearchEngine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PicksDashboard:
    """Dashboard for displaying picks with cards, filters, and analysis."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.ai_picks = AIPicks()
        self.research_engine = ResearchEngine()
    
    def get_pick_cards(self, filters: Dict = None) -> List[Dict]:
        """Get pick cards with all metadata."""
        if filters is None:
            filters = {}
        
        # Get games
        games = self.session.query(Game).filter(
            Game.status == "scheduled"
        ).all()
        
        # Apply sport filter
        if filters.get("sport"):
            games = [g for g in games if g.sport == filters["sport"]]
        
        # Get AI picks
        picks = self.ai_picks.generate_ai_picks(games, max_picks=50)
        
        # Apply bet type filter
        if filters.get("bet_type"):
            picks = [p for p in picks if p["leg"]["bet_type"] == filters["bet_type"]]
        
        # Apply prop type filter
        if filters.get("prop_type"):
            prop_type = filters["prop_type"].lower()
            picks = [p for p in picks if prop_type in (p["leg"].get("prop_type") or "").lower()]
        
        # Apply player filter
        if filters.get("player"):
            picks = [p for p in picks if filters["player"].lower() in (p["leg"].get("player_name") or "").lower()]
        
        # Apply game filter
        if filters.get("game_id"):
            picks = [p for p in picks if p["game"].id == filters["game_id"]]
        
        # Convert to pick cards
        cards = []
        for pick in picks:
            card = self._create_pick_card(pick)
            cards.append(card)
        
        # Sort by confidence
        cards.sort(key=lambda x: x["confidence"], reverse=True)
        
        return cards
    
    def _create_pick_card(self, pick: Dict) -> Dict:
        """Create a pick card with all metadata."""
        leg = pick["leg"]
        game = pick["game"]
        
        card = {
            "id": f"{game.id}_{leg.get('player_name', '')}_{leg['bet_type']}",
            "confidence": pick["confidence"],
            "confidence_level": self._get_confidence_level(pick["confidence"]),
            "ai_score": pick["ai_score"],
            "expected_value": pick["expected_value"],
            "odds": pick["odds"],
            "bet_type": leg["bet_type"],
            "selection": leg["selection"],
            "game": {
                "id": game.id,
                "sport": game.sport,
                "home_team": game.home_team or game.fighter1,
                "away_team": game.away_team or game.fighter2,
                "game_date": game.game_date
            },
            "line_movement": self._get_line_movement(game, leg),
            "historical_performance": {
                "win_rate": pick["historical_win_rate"],
                "data_points": pick["data_points"],
                "trend": pick["recent_trend"]
            },
            "ai_analysis": {
                "key_insights": pick["key_insights"],
                "reasoning": pick["reasoning"]
            },
            "player_name": leg.get("player_name"),
            "prop_type": leg.get("prop_type"),
            "prop_value": leg.get("prop_value")
        }
        
        return card
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Get confidence level label."""
        if confidence >= 0.85:
            return "🔥 Very High"
        elif confidence >= 0.75:
            return "🟢 High"
        elif confidence >= 0.65:
            return "🟡 Moderate"
        else:
            return "🔴 Low"
    
    def _get_line_movement(self, game: Game, leg: Dict) -> Dict:
        """Get line movement data (simulated for now)."""
        # In a real implementation, this would track actual line movement
        return {
            "opening_odds": leg["odds"] * 0.95,  # Simulated opening
            "current_odds": leg["odds"],
            "movement": "stable",  # stable, up, down
            "movement_pct": 0.0,
            "sportsbooks": ["DraftKings", "FanDuel", "BetMGM"]  # Simulated
        }
    
    def get_available_filters(self) -> Dict:
        """Get available filter options."""
        games = self.session.query(Game).filter(
            Game.status == "scheduled"
        ).all()
        
        sports = list(set(g.sport for g in games))
        bet_types = ["moneyline", "spread", "total", "prop", "fighter_moneyline"]
        
        # Get unique prop types
        props = self.session.query(PlayerProp).join(Game).filter(
            Game.status == "scheduled"
        ).all()
        prop_types = list(set(p.prop_type or p.market_key for p in props if p.prop_type or p.market_key))
        
        # Get unique players
        players = list(set(p.player_name for p in props if p.player_name))
        
        return {
            "sports": sports,
            "bet_types": bet_types,
            "prop_types": prop_types[:20],  # Limit to top 20
            "players": players[:50],  # Limit to top 50
            "games": [
                {
                    "id": g.id,
                    "display": f"{g.away_team or g.fighter2} @ {g.home_team or g.fighter1}",
                    "sport": g.sport
                }
                for g in games[:20]  # Limit to 20 games
            ]
        }

