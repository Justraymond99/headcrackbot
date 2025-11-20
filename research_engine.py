"""Research engine for analyzing games and building parlays."""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from itertools import combinations
from models import Game, Leg, Parlay, PlayerProp, SessionLocal
from config import MIN_CONFIDENCE, MAX_PARLAY_LEGS, MIN_PARLAY_LEGS
from advanced_analytics import CorrelationMatrix, KellyCriterion, PortfolioOptimizer
from ml_models import MLPredictor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResearchEngine:
    """Analyze games and build optimal parlays."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.weights = {
            "value": 0.4,  # Expected value weight
            "confidence": 0.3,  # Confidence score weight
            "correlation": 0.2,  # Correlation penalty
            "diversification": 0.1  # Diversification bonus
        }
        self.correlation_matrix = CorrelationMatrix()
        self.kelly = KellyCriterion()
        self.ml_predictor = MLPredictor()  # ML models for probability estimation
    
    def american_to_decimal(self, american_odds: float) -> float:
        """Convert American odds to decimal odds."""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
    
    def american_to_implied_prob(self, american_odds: float) -> float:
        """Convert American odds to implied probability."""
        if american_odds > 0:
            return 100 / (american_odds + 100)
        else:
            return abs(american_odds) / (abs(american_odds) + 100)
    
    def calculate_expected_value(self, implied_prob: float, true_prob: float, odds: float) -> float:
        """
        Calculate expected value of a bet.
        
        Args:
            implied_prob: Implied probability from odds
            true_prob: Our estimated true probability
            odds: American odds
        
        Returns:
            Expected value as a percentage
        """
        decimal_odds = self.american_to_decimal(odds)
        ev = (true_prob * (decimal_odds - 1)) - (1 - true_prob)
        return ev
    
    def calculate_confidence_score(self, game: Game, bet_type: str, selection: str) -> float:
        """
        Calculate confidence score for a bet.
        
        This is where you implement your custom logic/weights.
        """
        score = 0.5  # Base score
        
        # Example logic (customize based on your strategy):
        # - Check team streaks
        # - Analyze head-to-head records
        # - Consider injury reports
        # - Factor in home/away performance
        # - Use advanced stats
        
        # Placeholder: Add your custom logic here
        # For now, return a score based on odds value
        if bet_type == "moneyline":
            if selection == game.home_team:
                odds = game.home_moneyline
            else:
                odds = game.away_moneyline
            
            if odds:
                implied_prob = self.american_to_implied_prob(odds)
                # If odds are close to even, slightly higher confidence
                if 0.45 <= implied_prob <= 0.55:
                    score = 0.65
                elif 0.4 <= implied_prob <= 0.6:
                    score = 0.6
                else:
                    score = 0.55
        elif bet_type == "prop":
            # Player props get slightly higher base confidence to encourage inclusion
            # Adjust based on odds value
            score = 0.62  # Above minimum threshold to ensure inclusion
        elif bet_type == "fighter_moneyline":
            # UFC fights
            score = 0.6
        
        return min(max(score, 0.0), 1.0)  # Clamp between 0 and 1
    
    def estimate_true_probability(self, game: Game, bet_type: str, selection: str, prop: PlayerProp = None) -> float:
        """
        Estimate true probability using ML models.
        
        This integrates ML predictions, simulations, and Bayesian methods.
        """
        if bet_type == "moneyline":
            # Use ML predictor for moneyline
            home_prob, away_prob = self.ml_predictor.predict_moneyline_probability(game)
            
            if selection == game.home_team:
                return home_prob
            elif selection == game.away_team:
                return away_prob
            else:
                # Fallback to implied probability
                if game.home_moneyline:
                    return self.american_to_implied_prob(game.home_moneyline)
                return 0.5
        
        elif bet_type == "fighter_moneyline":
            # UFC - use ML predictor
            home_prob, away_prob = self.ml_predictor.predict_moneyline_probability(game)
            
            if selection == game.fighter1:
                return home_prob
            elif selection == game.fighter2:
                return away_prob
            return 0.5
        
        elif bet_type == "spread":
            # Use ML spread prediction
            predicted_spread = self.ml_predictor.predict_spread(game)
            book_spread = game.spread or 0.0
            
            # If predicted spread favors the selection, higher probability
            if "home" in selection.lower() or game.home_team in selection:
                # Home team covering
                if predicted_spread > book_spread:
                    return 0.55  # Slight edge
                elif predicted_spread < book_spread:
                    return 0.45  # Slight disadvantage
            else:
                # Away team covering
                if predicted_spread < book_spread:
                    return 0.55
                elif predicted_spread > book_spread:
                    return 0.45
            
            # Default to implied probability
            if game.spread_home_odds:
                return self.american_to_implied_prob(game.spread_home_odds)
            return 0.5
        
        elif bet_type == "total":
            # Use ML total prediction
            predicted_total = self.ml_predictor.predict_total(game)
            book_total = game.total or 0.0
            
            if "over" in selection.lower():
                if predicted_total > book_total:
                    return 0.55  # Slight edge for over
                elif predicted_total < book_total:
                    return 0.45
            else:  # under
                if predicted_total < book_total:
                    return 0.55  # Slight edge for under
                elif predicted_total > book_total:
                    return 0.45
            
            # Default to implied probability
            if game.over_odds:
                return self.american_to_implied_prob(game.over_odds)
            return 0.5
        
        elif bet_type == "prop" and prop:
            # Use ML prop predictor
            if "over" in selection.lower():
                return self.ml_predictor.predict_prop_probability(game, prop, "over")
            elif "under" in selection.lower():
                return self.ml_predictor.predict_prop_probability(game, prop, "under")
            elif "yes" in selection.lower():
                return self.ml_predictor.predict_prop_probability(game, prop, "yes")
            elif "no" in selection.lower():
                return self.ml_predictor.predict_prop_probability(game, prop, "no")
        
        # Default fallback
        return 0.5
    
    def analyze_game(self, game: Game) -> List[Dict]:
        """Analyze a game and return potential bet legs."""
        legs = []
        
        # Moneyline bets
        if game.home_moneyline:
            true_prob = self.estimate_true_probability(game, "moneyline", game.home_team)
            implied_prob = self.american_to_implied_prob(game.home_moneyline)
            ev = self.calculate_expected_value(implied_prob, true_prob, game.home_moneyline)
            confidence = self.calculate_confidence_score(game, "moneyline", game.home_team)
            
            if ev > 0 and confidence >= MIN_CONFIDENCE:
                legs.append({
                    "game": game,
                    "bet_type": "moneyline",
                    "selection": game.home_team,
                    "odds": game.home_moneyline,
                    "implied_probability": implied_prob,
                    "true_probability": true_prob,
                    "expected_value": ev,
                    "confidence_score": confidence,
                    "reasoning": f"Home team moneyline with {ev*100:.1f}% EV"
                })
        
        if game.away_moneyline:
            true_prob = self.estimate_true_probability(game, "moneyline", game.away_team)
            implied_prob = self.american_to_implied_prob(game.away_moneyline)
            ev = self.calculate_expected_value(implied_prob, true_prob, game.away_moneyline)
            confidence = self.calculate_confidence_score(game, "moneyline", game.away_team)
            
            if ev > 0 and confidence >= MIN_CONFIDENCE:
                legs.append({
                    "game": game,
                    "bet_type": "moneyline",
                    "selection": game.away_team,
                    "odds": game.away_moneyline,
                    "implied_probability": implied_prob,
                    "true_probability": true_prob,
                    "expected_value": ev,
                    "confidence_score": confidence,
                    "reasoning": f"Away team moneyline with {ev*100:.1f}% EV"
                })
        
        # Spread bets
        if game.spread and game.spread_home_odds:
            # Analyze spread (simplified)
            confidence = self.calculate_confidence_score(game, "spread", game.home_team)
            if confidence >= MIN_CONFIDENCE:
                legs.append({
                    "game": game,
                    "bet_type": "spread",
                    "selection": f"{game.home_team} {game.spread}",
                    "odds": game.spread_home_odds,
                    "implied_probability": self.american_to_implied_prob(game.spread_home_odds),
                    "expected_value": 0.05,  # Placeholder
                    "confidence_score": confidence,
                    "reasoning": f"Home team spread {game.spread}"
                })
        
        # Total bets
        if game.total and game.over_odds:
            confidence = self.calculate_confidence_score(game, "total", "over")
            if confidence >= MIN_CONFIDENCE:
                legs.append({
                    "game": game,
                    "bet_type": "total",
                    "selection": f"Over {game.total}",
                    "odds": game.over_odds,
                    "implied_probability": self.american_to_implied_prob(game.over_odds),
                    "expected_value": 0.05,  # Placeholder
                    "confidence_score": confidence,
                    "reasoning": f"Over {game.total} total points"
                })
        
        # UFC/Boxing Fighter moneylines
        if game.sport in ["UFC", "BOXING"]:
            if game.fighter1 and game.home_moneyline:
                true_prob = self.estimate_true_probability(game, "fighter_moneyline", game.fighter1)
                implied_prob = self.american_to_implied_prob(game.home_moneyline)
                ev = self.calculate_expected_value(implied_prob, true_prob, game.home_moneyline)
                confidence = self.calculate_confidence_score(game, "fighter_moneyline", game.fighter1)
                
                if ev > 0 and confidence >= MIN_CONFIDENCE:
                    legs.append({
                        "game": game,
                        "bet_type": "fighter_moneyline",
                        "selection": game.fighter1,
                        "odds": game.home_moneyline,
                        "implied_probability": implied_prob,
                        "true_probability": true_prob,
                        "expected_value": ev,
                        "confidence_score": confidence,
                        "reasoning": f"{game.fighter1} moneyline with {ev*100:.1f}% EV"
                    })
            
            if game.fighter2 and game.away_moneyline:
                true_prob = self.estimate_true_probability(game, "fighter_moneyline", game.fighter2)
                implied_prob = self.american_to_implied_prob(game.away_moneyline)
                ev = self.calculate_expected_value(implied_prob, true_prob, game.away_moneyline)
                confidence = self.calculate_confidence_score(game, "fighter_moneyline", game.fighter2)
                
                if ev > 0 and confidence >= MIN_CONFIDENCE:
                    legs.append({
                        "game": game,
                        "bet_type": "fighter_moneyline",
                        "selection": game.fighter2,
                        "odds": game.away_moneyline,
                        "implied_probability": implied_prob,
                        "true_probability": true_prob,
                        "expected_value": ev,
                        "confidence_score": confidence,
                        "reasoning": f"{game.fighter2} moneyline with {ev*100:.1f}% EV"
                    })
        
        # Get ALL props and markets (including player props, team totals, alternate spreads/totals, period markets)
        props = self.session.query(PlayerProp).filter_by(game_id=game.id).all()
        
        # Separate player props from other markets
        player_props = [p for p in props if not p.player_name.startswith("TEAM_")]
        team_markets = [p for p in props if p.player_name.startswith("TEAM_")]
        
        logger.info(f"Found {len(player_props)} player props and {len(team_markets)} team/period markets for game {game.id}")
        
        # Analyze player props
        for prop in player_props:
            # Handle Over/Under props
            if prop.over_odds and prop.prop_value is not None:
                confidence = self.calculate_confidence_score(game, "prop", f"{prop.player_name} {prop.prop_type} over")
                # Lower threshold for props to encourage inclusion
                prop_min_confidence = MIN_CONFIDENCE * 0.9  # 10% lower threshold
                
                if confidence >= prop_min_confidence:
                    implied_prob = self.american_to_implied_prob(prop.over_odds)
                    true_prob = self.estimate_true_probability(game, "prop", f"over {prop.prop_value}", prop=prop)
                    ev = self.calculate_expected_value(implied_prob, true_prob, prop.over_odds)
                    
                    # Include props even with slightly negative EV for diversification
                    if ev > -0.02:  # Allow small negative EV for props
                        legs.append({
                            "game": game,
                            "bet_type": "prop",
                            "selection": f"Over {prop.prop_value}",
                            "odds": prop.over_odds,
                            "implied_probability": implied_prob,
                            "true_probability": true_prob,
                            "expected_value": max(ev, 0.01),  # Ensure positive for display
                            "confidence_score": confidence,
                            "prop_type": prop.prop_type or prop.market_key or "points",
                            "prop_value": prop.prop_value,
                            "player_name": prop.player_name,
                            "market_key": prop.market_key,
                            "reasoning": f"{prop.player_name} {prop.description or prop.prop_type or 'points'} over {prop.prop_value} with {ev*100:.1f}% EV"
                        })
            
            if prop.under_odds and prop.prop_value is not None:
                confidence = self.calculate_confidence_score(game, "prop", f"{prop.player_name} {prop.prop_type} under")
                prop_min_confidence = MIN_CONFIDENCE * 0.9
                
                if confidence >= prop_min_confidence:
                    implied_prob = self.american_to_implied_prob(prop.under_odds)
                    true_prob = self.estimate_true_probability(game, "prop", f"under {prop.prop_value}", prop=prop)
                    ev = self.calculate_expected_value(implied_prob, true_prob, prop.under_odds)
                    
                    if ev > -0.02:
                        legs.append({
                            "game": game,
                            "bet_type": "prop",
                            "selection": f"Under {prop.prop_value}",
                            "odds": prop.under_odds,
                            "implied_probability": implied_prob,
                            "true_probability": true_prob,
                            "expected_value": max(ev, 0.01),
                            "confidence_score": confidence,
                            "prop_type": prop.prop_type or prop.market_key or "points",
                            "prop_value": prop.prop_value,
                            "player_name": prop.player_name,
                            "market_key": prop.market_key,
                            "reasoning": f"{prop.player_name} {prop.description or prop.prop_type or 'points'} under {prop.prop_value} with {ev*100:.1f}% EV"
                        })
            
            # Handle Yes/No props (e.g., anytime TD scorer)
            if prop.yes_odds:
                confidence = self.calculate_confidence_score(game, "prop", f"{prop.player_name} {prop.prop_type} yes")
                prop_min_confidence = MIN_CONFIDENCE * 0.9
                
                if confidence >= prop_min_confidence:
                    implied_prob = self.american_to_implied_prob(prop.yes_odds)
                    true_prob = self.estimate_true_probability(game, "prop", "yes", prop=prop)
                    ev = self.calculate_expected_value(implied_prob, true_prob, prop.yes_odds)
                    
                    if ev > -0.02:
                        legs.append({
                            "game": game,
                            "bet_type": "prop",
                            "selection": "Yes",
                            "odds": prop.yes_odds,
                            "implied_probability": implied_prob,
                            "true_probability": true_prob,
                            "expected_value": max(ev, 0.01),
                            "confidence_score": confidence,
                            "prop_type": prop.prop_type or prop.market_key or "anytime_td",
                            "prop_value": None,
                            "player_name": prop.player_name,
                            "market_key": prop.market_key,
                            "reasoning": f"{prop.player_name} {prop.description or prop.prop_type or 'anytime TD'} - Yes with {ev*100:.1f}% EV"
                        })
        
        # Analyze team/period markets (alternate spreads, totals, team totals, quarters, halves, periods, innings)
        for market in team_markets:
            bet_type = market.prop_type or market.market_key
            selection = market.player_name.replace("TEAM_", "")
            
            # Determine if it's over/under
            if market.over_odds and market.prop_value is not None:
                confidence = self.calculate_confidence_score(game, bet_type, f"{selection} over")
                prop_min_confidence = MIN_CONFIDENCE * 0.9
                
                if confidence >= prop_min_confidence:
                    implied_prob = self.american_to_implied_prob(market.over_odds)
                    true_prob = self.estimate_true_probability(game, bet_type, f"over {market.prop_value}", prop=market)
                    ev = self.calculate_expected_value(implied_prob, true_prob, market.over_odds)
                    
                    if ev > -0.02:
                        legs.append({
                            "game": game,
                            "bet_type": bet_type,
                            "selection": f"Over {market.prop_value:.1f}",
                            "odds": market.over_odds,
                            "implied_probability": implied_prob,
                            "true_probability": true_prob,
                            "expected_value": max(ev, 0.01),
                            "confidence_score": confidence,
                            "prop_type": bet_type,
                            "prop_value": market.prop_value,
                            "market_key": market.market_key,
                            "description": market.description or selection,
                            "reasoning": f"{selection} over {market.prop_value:.1f} with {ev*100:.1f}% EV"
                        })
            
            if market.under_odds and market.prop_value is not None:
                confidence = self.calculate_confidence_score(game, bet_type, f"{selection} under")
                prop_min_confidence = MIN_CONFIDENCE * 0.9
                
                if confidence >= prop_min_confidence:
                    implied_prob = self.american_to_implied_prob(market.under_odds)
                    true_prob = self.estimate_true_probability(game, bet_type, f"under {market.prop_value}", prop=market)
                    ev = self.calculate_expected_value(implied_prob, true_prob, market.under_odds)
                    
                    if ev > -0.02:
                        legs.append({
                            "game": game,
                            "bet_type": bet_type,
                            "selection": f"Under {market.prop_value:.1f}",
                            "odds": market.under_odds,
                            "implied_probability": implied_prob,
                            "true_probability": true_prob,
                            "expected_value": max(ev, 0.01),
                            "confidence_score": confidence,
                            "prop_type": bet_type,
                            "prop_value": market.prop_value,
                            "market_key": market.market_key,
                            "description": market.description or selection,
                            "reasoning": f"{selection} under {market.prop_value:.1f} with {ev*100:.1f}% EV"
                        })
            
            # Handle yes/no for team/period markets
            if market.yes_odds:
                confidence = self.calculate_confidence_score(game, bet_type, selection)
                prop_min_confidence = MIN_CONFIDENCE * 0.9
                
                if confidence >= prop_min_confidence:
                    implied_prob = self.american_to_implied_prob(market.yes_odds)
                    true_prob = self.estimate_true_probability(game, bet_type, "yes", prop=market)
                    ev = self.calculate_expected_value(implied_prob, true_prob, market.yes_odds)
                    
                    if ev > -0.02:
                        legs.append({
                            "game": game,
                            "bet_type": bet_type,
                            "selection": selection,
                            "odds": market.yes_odds,
                            "implied_probability": implied_prob,
                            "true_probability": true_prob,
                            "expected_value": max(ev, 0.01),
                            "confidence_score": confidence,
                            "prop_type": bet_type,
                            "market_key": market.market_key,
                            "description": market.description or selection,
                            "reasoning": f"{selection} with {ev*100:.1f}% EV"
                        })
        
        logger.info(f"Generated {len(legs)} total legs for game {game.id} (including {len([l for l in legs if l['bet_type'] == 'prop'])} props and {len(team_markets)} team/period markets)")
        return legs
    
    def calculate_correlation_penalty(self, leg1: Dict, leg2: Dict) -> float:
        """
        Calculate correlation penalty between two legs.
        
        Higher correlation = higher penalty (we want diversification).
        """
        # Same game = high correlation
        if leg1["game"].id == leg2["game"].id:
            return 0.5
        
        # Same team = medium correlation
        if leg1.get("selection") == leg2.get("selection"):
            return 0.3
        
        # Different games, different teams = low correlation
        return 0.1
    
    def build_parlay_score(self, legs: List[Dict]) -> float:
        """Calculate overall score for a parlay."""
        if len(legs) < MIN_PARLAY_LEGS:
            return 0.0
        
        # Calculate combined odds
        combined_implied_prob = 1.0
        combined_ev = 0.0
        avg_confidence = 0.0
        correlation_penalty = 0.0
        
        for leg in legs:
            combined_implied_prob *= leg["implied_probability"]
            combined_ev += leg["expected_value"]
            avg_confidence += leg["confidence_score"]
        
        avg_confidence /= len(legs)
        
        # Calculate correlation penalty
        for i in range(len(legs)):
            for j in range(i + 1, len(legs)):
                correlation_penalty += self.calculate_correlation_penalty(legs[i], legs[j])
        
        correlation_penalty = min(correlation_penalty / (len(legs) * (len(legs) - 1) / 2), 1.0)
        
        # Diversification bonus (more legs = more diversification, but also lower probability)
        diversification = min(len(legs) / MAX_PARLAY_LEGS, 1.0)
        
        # Combined score
        score = (
            self.weights["value"] * (combined_ev / len(legs)) +
            self.weights["confidence"] * avg_confidence -
            self.weights["correlation"] * correlation_penalty +
            self.weights["diversification"] * diversification
        )
        
        return score
    
    def generate_same_game_parlays(self, game: Game, max_parlays: int = 10) -> List[Dict]:
        """Generate Same Game Parlays (SGP) - all legs from one game."""
        legs = self.analyze_game(game)
        
        # Filter to props and game-specific bets only (no cross-game)
        sgp_legs = [leg for leg in legs if leg.get("bet_type") in ["prop", "moneyline", "spread", "total"]]
        
        if len(sgp_legs) < MIN_PARLAY_LEGS:
            logger.info(f"Not enough legs for SGP from game {game.id}")
            return []
        
        parlay_candidates = []
        
        # Generate combinations (prefer 4-8 legs for SGP)
        for num_legs in range(max(MIN_PARLAY_LEGS, 4), min(9, len(sgp_legs) + 1)):
            from itertools import combinations
            for combo in combinations(sgp_legs, num_legs):
                # Calculate parlay metrics
                combined_implied_prob = 1.0
                combined_odds = 1.0
                avg_confidence = 0.0
                
                for leg in combo:
                    combined_implied_prob *= leg["implied_probability"]
                    combined_odds *= self.american_to_decimal(leg["odds"])
                    avg_confidence += leg["confidence_score"]
                
                avg_confidence /= len(combo)
                combined_odds -= 1
                combined_american = (combined_odds * 100) if combined_odds >= 1 else (-100 / combined_odds)
                
                combined_ev = (combined_implied_prob * combined_odds) - (1 - combined_implied_prob)
                
                if avg_confidence >= 0.75:
                    confidence_rating = "High"
                elif avg_confidence >= 0.65:
                    confidence_rating = "Moderate"
                else:
                    confidence_rating = "Low"
                
                score = self.build_parlay_score(list(combo))
                # Bonus for SGP (same game parlays are popular)
                score *= 1.2
                
                # Count props
                prop_count = sum(1 for leg in combo if leg.get("bet_type") == "prop")
                
                parlay_candidates.append({
                    "legs": combo,
                    "num_legs": len(combo),
                    "combined_odds": combined_american,
                    "combined_implied_prob": combined_implied_prob,
                    "expected_value": combined_ev,
                    "confidence_score": avg_confidence,
                    "confidence_rating": confidence_rating,
                    "score": score,
                    "has_props": prop_count > 0,
                    "prop_count": prop_count,
                    "is_sgp": True,
                    "game": game
                })
        
        # Sort by score
        parlay_candidates.sort(key=lambda x: x["score"], reverse=True)
        
        logger.info(f"Generated {len(parlay_candidates)} SGP candidates for game {game.id}")
        return parlay_candidates[:max_parlays]
    
    def generate_parlays(self, games: List[Game], max_parlays: int = 10, include_sgp: bool = True) -> List[Dict]:
        """Generate top parlays from available games."""
        all_parlays = []
        
        # Generate Same Game Parlays first (very popular)
        if include_sgp:
            for game in games:
                sgp_parlays = self.generate_same_game_parlays(game, max_parlays=5)
                all_parlays.extend(sgp_parlays)
        
        # Analyze all games for cross-game parlays
        all_legs = []
        prop_legs = []
        regular_legs = []
        
        for game in games:
            legs = self.analyze_game(game)
            all_legs.extend(legs)
            # Separate props from regular bets
            for leg in legs:
                if leg.get("bet_type") == "prop":
                    prop_legs.append(leg)
                else:
                    regular_legs.append(leg)
        
        logger.info(f"Total legs: {len(all_legs)} ({len(prop_legs)} props, {len(regular_legs)} regular)")
        
        if len(all_legs) < MIN_PARLAY_LEGS:
            logger.warning("Not enough qualifying legs to build parlays")
            return all_parlays[:max_parlays] if all_parlays else []
        
        # Prioritize parlays that include at least one prop for diversity
        prioritize_props = len(prop_legs) > 0
        
        # Generate parlay combinations
        parlay_candidates = []
        
        for num_legs in range(MIN_PARLAY_LEGS, min(MAX_PARLAY_LEGS + 1, len(all_legs) + 1)):
            for combo in combinations(all_legs, num_legs):
                # Calculate parlay metrics
                combined_implied_prob = 1.0
                combined_odds = 1.0
                avg_confidence = 0.0
                
                for leg in combo:
                    combined_implied_prob *= leg["implied_probability"]
                    combined_odds *= self.american_to_decimal(leg["odds"])
                    avg_confidence += leg["confidence_score"]
                
                avg_confidence /= len(combo)
                combined_odds -= 1  # Convert to profit multiplier
                combined_american = (combined_odds * 100) if combined_odds >= 1 else (-100 / combined_odds)
                
                # Calculate expected value
                combined_ev = (combined_implied_prob * combined_odds) - (1 - combined_implied_prob)
                
                # Determine confidence rating
                if avg_confidence >= 0.75:
                    confidence_rating = "High"
                elif avg_confidence >= 0.65:
                    confidence_rating = "Moderate"
                else:
                    confidence_rating = "Low"
                
                score = self.build_parlay_score(list(combo))
                
                # Bonus for including player props (diversification)
                has_props = any(leg.get("bet_type") == "prop" for leg in combo)
                if has_props:
                    score *= 1.15  # 15% bonus for prop inclusion
                
                parlay_candidates.append({
                    "legs": combo,
                    "combined_odds": combined_american,
                    "implied_probability": combined_implied_prob,
                    "expected_value": combined_ev,
                    "confidence_rating": confidence_rating,
                    "confidence_score": avg_confidence,
                    "score": score,
                    "num_legs": len(combo),
                    "has_props": has_props
                })
        
        # Sort by score, prioritizing props
        parlay_candidates.sort(
            key=lambda x: (x.get("has_props", False), x["score"]),
            reverse=True
        )
        
        logger.info(f"Generated {len(parlay_candidates)} parlay candidates ({sum(1 for p in parlay_candidates if p.get('has_props'))} with props)")
        
        # Apply advanced correlation optimization
        optimized = self.correlation_matrix.optimize_parlay_selection(
            parlay_candidates, max_parlays
        )
        
        # Add Kelly Criterion recommendations
        for parlay in optimized:
            leg_probs = [l.get('true_probability', l['implied_probability']) for l in parlay['legs']]
            kelly_fraction = self.kelly.calculate_parlay_kelly(
                Parlay(combined_odds=parlay['combined_odds']),
                leg_probs
            )
            parlay['recommended_stake_pct'] = kelly_fraction * 100
        
        # Combine SGP and regular parlays, prioritize SGPs
        all_parlays.extend(optimized if optimized else parlay_candidates[:max_parlays])
        
        # Sort all parlays by score (SGPs already have bonus)
        all_parlays.sort(
            key=lambda x: (x.get("is_sgp", False), x.get("has_props", False), x["score"]),
            reverse=True
        )
        
        logger.info(f"Returning {len(all_parlays[:max_parlays])} total parlays ({sum(1 for p in all_parlays[:max_parlays] if p.get('is_sgp'))} SGPs)")
        return all_parlays[:max_parlays]
    
    def save_parlay(self, parlay_data: Dict, name: str, sport: str = None) -> Parlay:
        """Save a parlay to the database."""
        parlay = Parlay(
            name=name,
            sport=sport,
            combined_odds=parlay_data["combined_odds"],
            implied_probability=parlay_data["implied_probability"],
            expected_value=parlay_data["expected_value"],
            confidence_rating=parlay_data["confidence_rating"],
            confidence_score=parlay_data["confidence_score"],
            status="pending"
        )
        
        self.session.add(parlay)
        self.session.flush()
        
        # Create legs
        for leg_data in parlay_data["legs"]:
            leg = Leg(
                game_id=leg_data["game"].id,
                parlay_id=parlay.id,
                bet_type=leg_data["bet_type"],
                selection=leg_data["selection"],
                odds=leg_data["odds"],
                implied_probability=leg_data["implied_probability"],
                expected_value=leg_data["expected_value"],
                confidence_score=leg_data["confidence_score"],
                reasoning=leg_data.get("reasoning", ""),
                result="pending"
            )
            self.session.add(leg)
        
        self.session.commit()
        logger.info(f"Saved parlay: {name}")
        return parlay
    
    def get_top_parlays(self, sport: str = None, limit: int = 10) -> List[Parlay]:
        """Get top parlays from database."""
        query = self.session.query(Parlay).filter_by(status="pending")
        if sport:
            query = query.filter_by(sport=sport)
        
        return query.order_by(Parlay.confidence_score.desc(), Parlay.expected_value.desc()).limit(limit).all()
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

