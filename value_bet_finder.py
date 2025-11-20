"""Value bet finder - scan all games for positive EV bets."""
from typing import List, Dict, Optional
from datetime import datetime
from models import Game, ValueBet, SessionLocal
from research_engine import ResearchEngine
from ml_models import MLPredictor
from rapidapi_sportsbook import RapidAPISportsbook
import logging

logger = logging.getLogger(__name__)


class ValueBetFinder:
    """Find value bets across all games."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.research_engine = ResearchEngine()
        self.ml_predictor = MLPredictor()
        self.rapidapi = RapidAPISportsbook()
    
    def find_value_bets(
        self,
        min_ev: float = 0.05,
        min_confidence: float = 0.6,
        sports: Optional[List[str]] = None,
        max_results: int = 50,
        use_rapidapi: bool = True
    ) -> List[Dict]:
        """Find all value bets meeting criteria."""
        value_bets = []
        
        # First, try to get advantages from RapidAPI
        if use_rapidapi:
            try:
                logger.info("Fetching advantages from RapidAPI Sportsbook...")
                for sport in (sports or ["NBA", "NFL", "MLB", "NHL", "UFC"]):
                    api_value_bets = self.rapidapi.get_value_bets(sport=sport, min_edge=min_ev * 100)
                    for vb in api_value_bets:
                        # Convert to our format
                        value_bets.append({
                            "game": None,  # Will need to match with game in DB
                            "bet_type": vb.get("bet_type", "moneyline"),
                            "selection": vb.get("team") or vb.get("selection", "Unknown"),
                            "odds": vb.get("odds", 0),
                            "expected_value": vb.get("edge", 0) / 100 if vb.get("edge") else 0,
                            "edge_percentage": vb.get("edge", 0),
                            "confidence_score": vb.get("confidence", min_confidence),
                            "confidence_level": "High" if vb.get("confidence", 0) >= 0.75 else "Medium",
                            "value_score": (vb.get("edge", 0) / 100 * 0.6) + (vb.get("confidence", 0.6) * 0.4),
                            "true_probability": None,
                            "implied_probability": None,
                            "reasoning": vb.get("description", f"RapidAPI advantage: {vb.get('edge', 0)}% edge"),
                            "source": "rapidapi"
                        })
                logger.info(f"Found {len(value_bets)} value bets from RapidAPI")
            except Exception as e:
                logger.warning(f"Error fetching from RapidAPI: {e}, falling back to local analysis")
        
        # Get games for local analysis
        query = self.session.query(Game).filter(Game.status == "scheduled")
        if sports:
            query = query.filter(Game.sport.in_(sports))
        games = query.all()
        
        logger.info(f"Scanning {len(games)} games for value bets...")
        
        for game in games:
            # Analyze game for potential bets
            legs = self.research_engine.analyze_game(game)
            
            for leg in legs:
                ev = leg.get("expected_value", 0)
                confidence = leg.get("confidence_score", 0)
                
                # Check if meets criteria
                if ev >= min_ev and confidence >= min_confidence:
                    value_score = (ev * 0.6) + (confidence * 0.4)
                    
                    # Determine confidence level
                    if confidence >= 0.75:
                        conf_level = "High"
                    elif confidence >= 0.65:
                        conf_level = "Medium"
                    else:
                        conf_level = "Low"
                    
                    value_bet = {
                        "game": game,
                        "bet_type": leg["bet_type"],
                        "selection": leg["selection"],
                        "odds": leg["odds"],
                        "implied_probability": leg["implied_probability"],
                        "true_probability": leg.get("true_probability", leg["implied_probability"]),
                        "expected_value": ev,
                        "edge_percentage": ev * 100,
                        "value_score": value_score,
                        "confidence_level": conf_level,
                        "confidence_score": confidence,
                        "reasoning": leg.get("reasoning", ""),
                        "leg_data": leg
                    }
                    value_bets.append(value_bet)
        
        # Sort by value score
        value_bets.sort(key=lambda x: x["value_score"], reverse=True)
        
        logger.info(f"Found {len(value_bets)} value bets")
        return value_bets[:max_results]
    
    def save_value_bets(self, value_bets: List[Dict]):
        """Save value bets to database."""
        for vb in value_bets:
            # Check if already exists
            existing = self.session.query(ValueBet).filter_by(
                game_id=vb["game"].id,
                bet_type=vb["bet_type"],
                selection=vb["selection"]
            ).first()
            
            if existing:
                # Update
                existing.odds = vb["odds"]
                existing.implied_probability = vb["implied_probability"]
                existing.true_probability = vb["true_probability"]
                existing.expected_value = vb["expected_value"]
                existing.edge_percentage = vb["edge_percentage"]
                existing.value_score = vb["value_score"]
                existing.confidence_level = vb["confidence_level"]
                existing.confidence_score = vb["confidence_score"]
                existing.updated_at = datetime.utcnow()
            else:
                # Create new
                value_bet = ValueBet(
                    game_id=vb["game"].id,
                    bet_type=vb["bet_type"],
                    selection=vb["selection"],
                    odds=vb["odds"],
                    implied_probability=vb["implied_probability"],
                    true_probability=vb["true_probability"],
                    expected_value=vb["expected_value"],
                    edge_percentage=vb["edge_percentage"],
                    value_score=vb["value_score"],
                    confidence_level=vb["confidence_level"],
                    confidence_score=vb["confidence_score"]
                )
                self.session.add(value_bet)
        
        self.session.commit()
    
    def get_available_value_bets(self, limit: int = 20) -> List[ValueBet]:
        """Get available value bets from database."""
        return self.session.query(ValueBet).filter_by(
            status="available"
        ).order_by(ValueBet.value_score.desc()).limit(limit).all()
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

