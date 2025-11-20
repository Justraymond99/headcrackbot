"""Parlay optimizer - find optimal leg combinations."""
from typing import List, Dict, Optional, Tuple
from itertools import combinations
from models import Game, SessionLocal
from research_engine import ResearchEngine
import logging

logger = logging.getLogger(__name__)


class ParlayOptimizer:
    """Optimize parlay leg combinations."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.research_engine = ResearchEngine()
    
    def optimize_for_target_odds(
        self,
        games: List[Game],
        target_odds: float,
        tolerance: float = 0.1,
        min_legs: int = 2,
        max_legs: int = 8
    ) -> List[Dict]:
        """Find parlay combinations closest to target odds."""
        # Get all potential legs
        all_legs = []
        for game in games:
            legs = self.research_engine.analyze_game(game)
            all_legs.extend(legs)
        
        if len(all_legs) < min_legs:
            return []
        
        candidates = []
        
        # Try different leg counts
        for num_legs in range(min_legs, min(max_legs + 1, len(all_legs) + 1)):
            for combo in combinations(all_legs, num_legs):
                # Calculate combined odds
                combined_implied = 1.0
                combined_odds = 1.0
                total_ev = 0.0
                total_confidence = 0.0
                
                for leg in combo:
                    combined_implied *= leg["implied_probability"]
                    combined_odds *= self.research_engine.american_to_decimal(leg["odds"])
                    total_ev += leg.get("expected_value", 0)
                    total_confidence += leg.get("confidence_score", 0)
                
                combined_odds -= 1
                combined_american = (combined_odds * 100) if combined_odds >= 1 else (-100 / combined_odds)
                
                # Check if close to target
                diff = abs(combined_american - target_odds) / target_odds
                
                if diff <= tolerance:
                    candidates.append({
                        "legs": combo,
                        "num_legs": num_legs,
                        "combined_odds": combined_american,
                        "implied_probability": combined_implied,
                        "expected_value": total_ev / num_legs,
                        "confidence_score": total_confidence / num_legs,
                        "target_diff": diff,
                        "score": (1 - diff) * (total_ev / num_legs) * (total_confidence / num_legs)
                    })
        
        # Sort by score
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:10]
    
    def maximize_ev(
        self,
        games: List[Game],
        max_legs: int = 5,
        min_confidence: float = 0.6
    ) -> List[Dict]:
        """Find parlay with maximum expected value."""
        all_legs = []
        for game in games:
            legs = self.research_engine.analyze_game(game)
            # Filter by confidence
            legs = [l for l in legs if l.get("confidence_score", 0) >= min_confidence]
            all_legs.extend(legs)
        
        if len(all_legs) < 2:
            return []
        
        candidates = []
        
        for num_legs in range(2, min(max_legs + 1, len(all_legs) + 1)):
            for combo in combinations(all_legs, num_legs):
                combined_implied = 1.0
                combined_odds = 1.0
                total_ev = 0.0
                total_confidence = 0.0
                
                for leg in combo:
                    combined_implied *= leg["implied_probability"]
                    combined_odds *= self.research_engine.american_to_decimal(leg["odds"])
                    total_ev += leg.get("expected_value", 0)
                    total_confidence += leg.get("confidence_score", 0)
                
                combined_odds -= 1
                combined_american = (combined_odds * 100) if combined_odds >= 1 else (-100 / combined_odds)
                
                # Combined EV for parlay
                parlay_ev = (combined_implied * combined_odds) - (1 - combined_implied)
                
                candidates.append({
                    "legs": combo,
                    "num_legs": num_legs,
                    "combined_odds": combined_american,
                    "implied_probability": combined_implied,
                    "expected_value": parlay_ev,
                    "confidence_score": total_confidence / num_legs,
                    "score": parlay_ev * (total_confidence / num_legs)
                })
        
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:10]
    
    def round_robin_generator(
        self,
        legs: List[Dict],
        group_size: int = 3
    ) -> List[Dict]:
        """Generate round-robin parlays."""
        if len(legs) < group_size:
            return []
        
        round_robins = []
        
        for combo in combinations(legs, group_size):
            combined_implied = 1.0
            combined_odds = 1.0
            
            for leg in combo:
                combined_implied *= leg["implied_probability"]
                combined_odds *= self.research_engine.american_to_decimal(leg["odds"])
            
            combined_odds -= 1
            combined_american = (combined_odds * 100) if combined_odds >= 1 else (-100 / combined_odds)
            
            round_robins.append({
                "legs": combo,
                "num_legs": group_size,
                "combined_odds": combined_american,
                "implied_probability": combined_implied
            })
        
        return round_robins
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

