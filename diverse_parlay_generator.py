"""Generate diverse parlays from each sport with varied bet types and line amounts."""
import logging
from typing import List, Dict, Optional
from itertools import combinations
from datetime import datetime, timedelta
from models import Game, SessionLocal
from ai_picks import AIPicks
from research_engine import ResearchEngine
from config import MIN_PARLAY_LEGS, MAX_PARLAY_LEGS

logger = logging.getLogger(__name__)


class DiverseParlayGenerator:
    """Generate diverse parlays with varied bet types and line amounts from each sport."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.research_engine = ResearchEngine()
        self.ai_picks = AIPicks()
    
    def generate_diverse_sport_parlays(
        self,
        games: List[Game],
        sport: str,
        max_parlays: int = 3,
        ensure_variety: bool = True
    ) -> List[Dict]:
        """
        Generate diverse parlays from a specific sport.
        
        Ensures variety in:
        - Leg counts (2-15 legs)
        - Bet types (moneylines, spreads, totals, props, alternate spreads, team totals, periods)
        - Line amounts (alternate spreads, alternate totals)
        
        Args:
            games: List of games for the sport
            sport: Sport abbreviation
            max_parlays: Maximum number of parlays to return
            ensure_variety: Whether to ensure variety in bet types and leg counts
        
        Returns:
            List of parlay dictionaries with diverse options
        """
        if not games:
            return []
        
        # Get all legs from games
        all_legs = []
        for game in games:
            legs = self.research_engine.analyze_game(game)
            all_legs.extend(legs)
        
        if len(all_legs) < 2:
            return []
        
        logger.info(f"Found {len(all_legs)} total legs for {sport}")
        
        # Categorize legs by bet type for variety
        legs_by_type = {
            "moneyline": [],
            "spread": [],
            "total": [],
            "prop": [],
            "alternate_spread": [],
            "alternate_total": [],
            "team_total": [],
            "quarter": [],
            "half": [],
            "period": [],
            "innings": []
        }
        
        for leg in all_legs:
            bet_type = leg.get("bet_type", "moneyline")
            
            # Categorize
            if bet_type == "moneyline" or bet_type == "fighter_moneyline" or bet_type == "boxing_moneyline":
                legs_by_type["moneyline"].append(leg)
            elif "alternate_spread" in bet_type:
                legs_by_type["alternate_spread"].append(leg)
            elif bet_type == "spread":
                legs_by_type["spread"].append(leg)
            elif "alternate_total" in bet_type:
                legs_by_type["alternate_total"].append(leg)
            elif bet_type == "total":
                legs_by_type["total"].append(leg)
            elif bet_type == "team_total":
                legs_by_type["team_total"].append(leg)
            elif "quarter" in bet_type or "_q1" in bet_type or "_q2" in bet_type or "_q3" in bet_type or "_q4" in bet_type:
                legs_by_type["quarter"].append(leg)
            elif "half" in bet_type or "_h1" in bet_type or "_h2" in bet_type:
                legs_by_type["half"].append(leg)
            elif "period" in bet_type or "_p1" in bet_type or "_p2" in bet_type or "_p3" in bet_type:
                legs_by_type["period"].append(leg)
            elif "innings" in bet_type:
                legs_by_type["innings"].append(leg)
            elif bet_type == "prop":
                legs_by_type["prop"].append(leg)
        
        # Generate diverse parlays
        parlay_candidates = []
        
        if ensure_variety:
            # Generate parlays with different leg counts and bet type combinations
            leg_count_targets = [2, 3, 4, 5, 6, 7, 8, 10, 12, 15]  # Variety in leg counts
            
            for target_legs in leg_count_targets:
                if target_legs > len(all_legs):
                    continue
                
                # Generate parlays with different bet type combinations
                parlay_candidates.extend(
                    self._generate_varied_parlays(
                        all_legs,
                        legs_by_type,
                        target_legs,
                        sport
                    )
                )
        else:
            # Simple approach - just generate combinations
            for num_legs in range(MIN_PARLAY_LEGS, min(MAX_PARLAY_LEGS + 1, len(all_legs) + 1)):
                for combo in combinations(all_legs[:50], num_legs):
                    parlay = self._calculate_parlay_metrics(combo, sport)
                    if parlay:
                        parlay_candidates.append(parlay)
        
        # Sort by quality score (combination of odds, confidence, variety)
        parlay_candidates.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
        
        # Deduplicate similar parlays
        unique_parlays = self._deduplicate_parlays(parlay_candidates)
        
        logger.info(f"Generated {len(unique_parlays)} diverse parlay candidates for {sport}")
        
        return unique_parlays[:max_parlays]
    
    def _generate_varied_parlays(
        self,
        all_legs: List[Dict],
        legs_by_type: Dict[str, List[Dict]],
        target_legs: int,
        sport: str
    ) -> List[Dict]:
        """Generate parlays with varied bet types."""
        parlays = []
        
        # Different bet type combinations for variety
        type_combinations = [
            # Mix of main bet types
            (["moneyline", "spread", "total"], target_legs),
            # Include props
            (["moneyline", "spread", "total", "prop"], target_legs),
            # Include alternate lines
            (["moneyline", "alternate_spread", "alternate_total"], target_legs),
            # Include team totals
            (["moneyline", "team_total", "prop"], target_legs),
            # Include period markets
            (["moneyline", "quarter", "half"], target_legs),
            # Heavy props
            (["prop", "moneyline"], target_legs),
            # Heavy alternate lines
            (["alternate_spread", "alternate_total", "moneyline"], target_legs),
        ]
        
        for type_combo, num_legs in type_combinations:
            selected_legs = []
            
            # Select legs from each type
            for leg_type in type_combo:
                legs = legs_by_type.get(leg_type, [])
                if legs:
                    # Take a few from each type
                    num_from_type = max(1, num_legs // len(type_combo))
                    selected_legs.extend(legs[:num_from_type])
            
            # If we need more legs, fill from all_legs
            while len(selected_legs) < num_legs and len(selected_legs) < len(all_legs):
                remaining = [l for l in all_legs if l not in selected_legs]
                if remaining:
                    selected_legs.append(remaining[0])
                else:
                    break
            
            # Take exactly num_legs
            if len(selected_legs) >= num_legs:
                for combo in combinations(selected_legs[:num_legs], num_legs):
                    parlay = self._calculate_parlay_metrics(list(combo), sport)
                    if parlay:
                        parlays.append(parlay)
                        if len(parlays) >= 5:  # Limit per combination
                            break
        
        return parlays
    
    def _calculate_parlay_metrics(self, legs: List[Dict], sport: str) -> Optional[Dict]:
        """Calculate metrics for a parlay."""
        if len(legs) < 2:
            return None
        
        # Ensure different games (diversification)
        game_ids = set(leg["game"].id for leg in legs)
        if len(game_ids) < max(2, len(legs) * 0.5):
            return None  # Too many from same game
        
        # Calculate combined odds and confidence
        combined_odds = 1.0
        combined_confidence = 1.0
        total_ev = 0.0
        
        bet_types_included = set()
        
        for leg in legs:
            odds = leg.get("odds", 0)
            if odds == 0:
                return None
            
            decimal_odds = self.research_engine.american_to_decimal(odds)
            combined_odds *= decimal_odds
            combined_confidence *= leg.get("confidence_score", 0.5)
            total_ev += leg.get("expected_value", 0)
            
            bet_types_included.add(leg.get("bet_type", "unknown"))
        
        combined_odds -= 1  # Convert to profit multiplier
        combined_american = (combined_odds * 100) if combined_odds >= 1 else (-100 / combined_odds)
        
        # Calculate potential payouts
        decimal_odds = combined_odds + 1
        potential_payouts = {
            "stake_10": 10 * decimal_odds,
            "stake_25": 25 * decimal_odds,
            "stake_50": 50 * decimal_odds,
            "stake_100": 100 * decimal_odds
        }
        
        # Quality score factors in:
        # - Combined confidence
        # - Number of bet types (variety bonus)
        # - Number of games (diversification)
        # - Expected value
        variety_bonus = 1.0 + (len(bet_types_included) - 1) * 0.1
        diversification_bonus = 1.0 + (len(game_ids) / len(legs)) * 0.1
        avg_ev = total_ev / len(legs)
        
        quality_score = (
            combined_confidence * 100 *  # Confidence
            variety_bonus *  # Bet type variety
            diversification_bonus *  # Game diversification
            (1 + avg_ev * 10)  # Expected value
        )
        
        return {
            "picks": legs,
            "num_legs": len(legs),
            "sport": sport,
            "combined_odds": combined_american,
            "decimal_odds": decimal_odds,
            "combined_confidence": combined_confidence,
            "potential_payouts": potential_payouts,
            "bet_types": list(bet_types_included),
            "num_games": len(game_ids),
            "avg_expected_value": avg_ev,
            "quality_score": quality_score,
            "legs": legs
        }
    
    def _deduplicate_parlays(self, parlays: List[Dict]) -> List[Dict]:
        """Remove duplicate or very similar parlays."""
        unique = []
        seen_signatures = set()
        
        for parlay in parlays:
            # Create signature from leg game IDs and selections
            picks = parlay.get("picks", parlay.get("legs", []))
            signature = tuple(
                sorted((pick["game"].id, pick.get("selection", "")) for pick in picks)
            )
            
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique.append(parlay)
        
        return unique
    
    def get_best_parlay_per_sport(
        self,
        max_parlays_per_sport: int = 1,
        min_confidence: float = 0.5
    ) -> Dict[str, List[Dict]]:
        """
        Get the best parlay from each sport.
        
        Args:
            max_parlays_per_sport: Maximum parlays per sport
            min_confidence: Minimum combined confidence
        
        Returns:
            Dictionary mapping sport to list of best parlays
        """
        from config import DEFAULT_SPORTS
        
        sport_parlays = {}
        
        # Get games grouped by sport
        tomorrow = datetime.now() + timedelta(days=1)
        all_games = self.session.query(Game).filter(
            Game.status == "scheduled",
            Game.game_date <= tomorrow
        ).all()
        
        games_by_sport = {}
        for game in all_games:
            if game.sport not in games_by_sport:
                games_by_sport[game.sport] = []
            games_by_sport[game.sport].append(game)
        
        # Generate best parlay for each sport
        for sport in DEFAULT_SPORTS:
            games = games_by_sport.get(sport, [])
            if not games:
                continue
            
            parlays = self.generate_diverse_sport_parlays(
                games,
                sport,
                max_parlays=max_parlays_per_sport,
                ensure_variety=True
            )
            
            # Filter by minimum confidence
            filtered = [
                p for p in parlays
                if p.get("combined_confidence", 0) >= min_confidence
            ]
            
            if filtered:
                sport_parlays[sport] = filtered
        
        return sport_parlays
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()


if __name__ == "__main__":
    from datetime import datetime, timedelta
    
    generator = DiverseParlayGenerator()
    parlays_by_sport = generator.get_best_parlay_per_sport(max_parlays_per_sport=1)
    
    for sport, parlays in parlays_by_sport.items():
        print(f"\n{sport}:")
        for parlay in parlays:
            print(f"  {parlay['num_legs']}-leg parlay: {parlay['combined_odds']:.0f} odds, "
                  f"{parlay['combined_confidence']*100:.1f}% confidence, "
                  f"bet types: {parlay['bet_types']}")

