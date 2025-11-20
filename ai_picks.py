"""AI Picks - Advanced analysis using historical data and multiple data points."""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Game, Leg, Parlay, PlayerProp, SessionLocal
from research_engine import ResearchEngine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIPicks:
    """AI system that scans data and finds best plays backed by historical outcomes."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.research_engine = ResearchEngine()
        self.min_data_points = 10  # Minimum historical data points (lowered for new systems)
        self.confidence_threshold = 0.55  # Lowered threshold to work with limited data
    
    def analyze_historical_performance(self, game: Game, bet_type: str, selection: str) -> Dict:
        """Analyze historical performance for a specific bet."""
        analysis = {
            "historical_win_rate": 0.55,  # Default to slightly above 50% when no data
            "recent_trend": "neutral",
            "data_points": 0,
            "confidence": 0.6,  # Base confidence when no historical data
            "key_insights": []
        }
        
        # Analyze past parlays with similar bets
        similar_legs = self.session.query(Leg).join(Game).filter(
            Game.sport == game.sport,
            Leg.bet_type == bet_type
        ).all()
        
        if len(similar_legs) > 0:
            # Calculate win rate from historical data
            won_legs = [l for l in similar_legs if l.parlay and l.parlay.result == "won"]
            total_with_results = [l for l in similar_legs if l.parlay and l.parlay.result in ["won", "lost"]]
            
            if total_with_results:
                analysis["historical_win_rate"] = len(won_legs) / len(total_with_results)
                analysis["data_points"] = len(total_with_results)
                
                # Recent trend (last 10 bets if available)
                recent_legs = total_with_results[-10:] if len(total_with_results) >= 10 else total_with_results
                recent_wins = sum(1 for l in recent_legs if l.parlay and l.parlay.result == "won")
                recent_rate = recent_wins / len(recent_legs) if recent_legs else 0.0
                
                if recent_rate > analysis["historical_win_rate"] * 1.1:
                    analysis["recent_trend"] = "hot"
                elif recent_rate < analysis["historical_win_rate"] * 0.9:
                    analysis["recent_trend"] = "cold"
                
                # Calculate confidence based on data quality
                # More data = higher confidence, but still work with limited data
                data_quality = min(analysis["data_points"] / 50, 1.0)  # Normalize to 50 data points
                analysis["confidence"] = 0.5 + (analysis["historical_win_rate"] - 0.5) * 0.5 + data_quality * 0.2
                analysis["confidence"] = min(max(analysis["confidence"], 0.5), 0.95)
                
                # Generate insights
                if analysis["historical_win_rate"] > 0.6:
                    analysis["key_insights"].append(f"Strong historical win rate: {analysis['historical_win_rate']*100:.1f}%")
                elif analysis["historical_win_rate"] < 0.4:
                    analysis["key_insights"].append(f"Below average historical performance: {analysis['historical_win_rate']*100:.1f}%")
                
                if analysis["recent_trend"] == "hot":
                    analysis["key_insights"].append("🔥 Hot recent trend - performing above average")
                elif analysis["recent_trend"] == "cold":
                    analysis["key_insights"].append("❄️ Cold recent trend - below average performance")
                
                if analysis["data_points"] >= 50:
                    analysis["key_insights"].append(f"Based on {analysis['data_points']} historical data points")
                elif analysis["data_points"] > 0:
                    analysis["key_insights"].append(f"Limited data: {analysis['data_points']} historical points (more data will improve accuracy)")
            else:
                # No results yet, but we have legs
                analysis["data_points"] = len(similar_legs)
                analysis["key_insights"].append("No results yet - using current analysis")
        else:
            # No historical data at all
            analysis["key_insights"].append("No historical data - using current EV and confidence analysis")
            analysis["key_insights"].append("💡 Tip: Lock some parlays and update results to build historical data")
        
        return analysis
    
    def generate_ai_picks(self, games: List[Game], max_picks: int = 10) -> List[Dict]:
        """Generate AI picks by analyzing multiple data points."""
        all_picks = []
        
        for game in games:
            # Analyze all potential bets for this game
            legs = self.research_engine.analyze_game(game)
            
            for leg in legs:
                # Get historical analysis
                historical = self.analyze_historical_performance(
                    game, leg["bet_type"], leg["selection"]
                )
                
                # Combine with research engine analysis
                # Adjust weights based on data availability
                if historical["data_points"] > 0:
                    # We have some historical data
                    combined_confidence = (
                        leg["confidence_score"] * 0.5 +  # Current analysis weight
                        historical["confidence"] * 0.5   # Historical weight
                    )
                    historical_weight = 0.3
                else:
                    # No historical data, rely more on current analysis
                    combined_confidence = leg["confidence_score"] * 0.9 + 0.1  # Slight boost
                    historical_weight = 0.1
                
                # Calculate AI score (combines multiple factors)
                # Adjust scoring based on data availability
                if historical["data_points"] > 0:
                    ai_score = (
                        leg["expected_value"] * 0.3 +           # EV weight
                        combined_confidence * 0.3 +             # Confidence weight
                        historical["historical_win_rate"] * historical_weight +  # Historical win rate
                        (1.0 if historical["recent_trend"] == "hot" else 0.8 if historical["recent_trend"] == "neutral" else 0.6) * 0.1 +  # Trend bonus
                        (min(historical["data_points"] / 50, 1.0)) * 0.1  # Data quality (normalized to 50)
                    )
                else:
                    # No historical data - use current analysis only
                    ai_score = (
                        leg["expected_value"] * 0.4 +           # Higher EV weight
                        combined_confidence * 0.4 +             # Higher confidence weight
                        0.55 * historical_weight +              # Neutral historical assumption
                        0.8 * 0.1 +                             # Neutral trend
                        0.3 * 0.1                               # Low data quality penalty
                    )
                
                # Lower threshold when no historical data
                threshold = self.confidence_threshold if historical["data_points"] > 0 else 0.5
                
                if combined_confidence >= threshold:
                    pick = {
                        "game": game,
                        "leg": leg,
                        "ai_score": ai_score,
                        "confidence": combined_confidence,
                        "expected_value": leg["expected_value"],
                        "historical_win_rate": historical["historical_win_rate"],
                        "recent_trend": historical["recent_trend"],
                        "data_points": historical["data_points"],
                        "key_insights": historical["key_insights"],
                        "reasoning": leg["reasoning"],
                        "odds": leg["odds"]
                    }
                    all_picks.append(pick)
        
        # Sort by AI score
        all_picks.sort(key=lambda x: x["ai_score"], reverse=True)
        
        logger.info(f"Generated {len(all_picks)} AI picks from {len(games)} games")
        return all_picks[:max_picks]
    
    def generate_ai_parlays(self, games: List[Game], max_parlays: int = 5) -> List[Dict]:
        """Generate AI-optimized parlays using advanced analysis."""
        # Get AI picks first
        ai_picks = self.generate_ai_picks(games, max_picks=50)
        
        if len(ai_picks) < 2:
            return []
        
        # Build parlays from top AI picks
        from itertools import combinations
        
        parlay_candidates = []
        
        # Support up to 15 leg parlays
        max_legs = min(15, len(ai_picks) + 1)
        for num_legs in range(2, max_legs):
            # Use more picks for larger parlays
            picks_to_use = min(50, len(ai_picks)) if num_legs > 5 else min(20, len(ai_picks))
            for combo in combinations(ai_picks[:picks_to_use], num_legs):
                # Check if picks are from different games (diversification)
                games_in_parlay = set(pick["game"].id for pick in combo)
                if len(games_in_parlay) < len(combo) * 0.5:  # At least 50% different games
                    continue
                
                # Calculate parlay metrics
                combined_odds = 1.0
                combined_confidence = 1.0
                total_ai_score = 0.0
                
                for pick in combo:
                    combined_odds *= self.research_engine.american_to_decimal(pick["odds"])
                    combined_confidence *= pick["confidence"]
                    total_ai_score += pick["ai_score"]
                
                combined_odds -= 1
                combined_american = (combined_odds * 100) if combined_odds >= 1 else (-100 / combined_odds)
                avg_ai_score = total_ai_score / len(combo)
                
                # Calculate potential payouts for different stake amounts
                decimal_odds = combined_odds + 1
                potential_payouts = {
                    "stake_10": 10 * decimal_odds,
                    "stake_25": 25 * decimal_odds,
                    "stake_50": 50 * decimal_odds,
                    "stake_100": 100 * decimal_odds
                }
                
                parlay_candidates.append({
                    "picks": combo,
                    "num_legs": len(combo),
                    "combined_odds": combined_american,
                    "decimal_odds": decimal_odds,
                    "combined_confidence": combined_confidence,
                    "ai_score": avg_ai_score,
                    "potential_payouts": potential_payouts,
                    "legs": [pick["leg"] for pick in combo]
                })
        
        # Sort by AI score
        parlay_candidates.sort(key=lambda x: x["ai_score"], reverse=True)
        
        logger.info(f"Generated {len(parlay_candidates)} AI parlay candidates")
        return parlay_candidates[:max_parlays]
    
    def get_pick_confidence_level(self, confidence: float) -> str:
        """Get human-readable confidence level."""
        if confidence >= 0.85:
            return "🔥 Very High"
        elif confidence >= 0.75:
            return "🟢 High"
        elif confidence >= 0.65:
            return "🟡 Moderate"
        else:
            return "🔴 Low"

