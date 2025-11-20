"""Advanced analytics and optimization tools."""
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from scipy.optimize import minimize
from models import Leg, Parlay, Game, SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KellyCriterion:
    """Kelly Criterion for optimal bet sizing."""
    
    @staticmethod
    def calculate_kelly_fraction(win_prob: float, odds: float, bankroll: float = 1000.0) -> float:
        """
        Calculate optimal bet size using Kelly Criterion.
        
        Args:
            win_prob: True probability of winning (0-1)
            odds: Decimal odds (e.g., 2.0 for even money)
            bankroll: Current bankroll
        
        Returns:
            Optimal bet size as fraction of bankroll
        """
        if win_prob <= 0 or win_prob >= 1:
            return 0.0
        
        # Convert American odds to decimal if needed
        if odds < 0:
            decimal_odds = (100 / abs(odds)) + 1
        elif odds > 0:
            decimal_odds = (odds / 100) + 1
        else:
            return 0.0
        
        # Kelly formula: f = (bp - q) / b
        # where b = odds - 1, p = win prob, q = 1 - p
        b = decimal_odds - 1
        q = 1 - win_prob
        kelly_fraction = (b * win_prob - q) / b
        
        # Fractional Kelly (use 25% for safety)
        fractional_kelly = kelly_fraction * 0.25
        
        # Ensure non-negative and capped at 5% of bankroll
        return max(0.0, min(fractional_kelly, 0.05))
    
    @staticmethod
    def calculate_parlay_kelly(parlay: Parlay, leg_probs: List[float], bankroll: float = 1000.0) -> float:
        """Calculate Kelly fraction for a parlay."""
        # Combined probability
        combined_prob = np.prod(leg_probs)
        
        # Convert combined odds to decimal
        if parlay.combined_odds < 0:
            decimal_odds = (100 / abs(parlay.combined_odds)) + 1
        else:
            decimal_odds = (parlay.combined_odds / 100) + 1
        
        return KellyCriterion.calculate_kelly_fraction(combined_prob, decimal_odds, bankroll)


class CorrelationMatrix:
    """Advanced correlation analysis for parlay optimization."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def calculate_team_correlation(self, team1: str, team2: str, sport: str) -> float:
        """Calculate historical correlation between two teams."""
        # Placeholder - would use historical game results
        # For now, return low correlation for different teams
        if team1 == team2:
            return 1.0
        return 0.1  # Low correlation between different teams
    
    def calculate_market_correlation(self, leg1: Leg, leg2: Leg) -> float:
        """Calculate correlation between two betting markets."""
        # Same game = high correlation
        if leg1.game_id == leg2.game_id:
            if leg1.bet_type == leg2.bet_type:
                return 0.9  # Same market, same game
            elif leg1.bet_type == "moneyline" and leg2.bet_type == "spread":
                return 0.7  # Related markets
            else:
                return 0.5  # Different markets, same game
        return 0.1  # Different games
    
    def build_correlation_matrix(self, legs) -> np.ndarray:
        """Build correlation matrix for a set of legs (can be Leg objects or dicts)."""
        n = len(legs)
        matrix = np.eye(n)  # Identity matrix (self-correlation = 1)
        
        for i in range(n):
            for j in range(i + 1, n):
                leg1 = legs[i]
                leg2 = legs[j]
                
                # Handle both Leg objects and dictionaries
                if isinstance(leg1, dict):
                    corr = self._calculate_dict_correlation(leg1, leg2)
                else:
                    corr = self.calculate_market_correlation(leg1, leg2)
                
                matrix[i][j] = corr
                matrix[j][i] = corr
        
        return matrix
    
    def _calculate_dict_correlation(self, leg1: Dict, leg2: Dict) -> float:
        """Calculate correlation between two leg dictionaries."""
        game1 = leg1.get('game')
        game2 = leg2.get('game')
        
        # Check if same game (by ID or by team names)
        same_game = False
        if game1 and game2:
            # Try by ID first
            if hasattr(game1, 'id') and hasattr(game2, 'id') and game1.id == game2.id:
                same_game = True
            # Fallback to team comparison
            elif (hasattr(game1, 'home_team') and hasattr(game2, 'home_team') and
                  hasattr(game1, 'away_team') and hasattr(game2, 'away_team')):
                if (game1.home_team == game2.home_team and 
                    game1.away_team == game2.away_team):
                    same_game = True
        
        if same_game:
            bet_type1 = leg1.get('bet_type', '')
            bet_type2 = leg2.get('bet_type', '')
            
            if bet_type1 == bet_type2:
                return 0.9  # Same market, same game
            elif bet_type1 == "moneyline" and bet_type2 == "spread":
                return 0.7  # Related markets
            else:
                return 0.5  # Different markets, same game
        
        return 0.1  # Different games
    
    def optimize_parlay_selection(self, parlay_candidates: List[Dict], max_parlays: int = 5) -> List[Dict]:
        """Optimize parlay selection using correlation and diversification."""
        if not parlay_candidates:
            return []
        
        # Score each parlay considering correlation
        scored_parlays = []
        for parlay in parlay_candidates:
            legs = parlay['legs']
            # Pass the leg dictionaries directly, not the games
            corr_matrix = self.build_correlation_matrix(legs)
            
            # Calculate average correlation (lower is better for diversification)
            avg_corr = np.mean(corr_matrix[np.triu_indices_from(corr_matrix, k=1)])
            
            # Adjust score: lower correlation = higher score
            diversification_bonus = (1 - avg_corr) * 0.2
            adjusted_score = parlay['score'] + diversification_bonus
            
            scored_parlays.append({
                **parlay,
                'avg_correlation': avg_corr,
                'adjusted_score': adjusted_score
            })
        
        # Sort by adjusted score
        scored_parlays.sort(key=lambda x: x['adjusted_score'], reverse=True)
        
        # Select diverse parlays (avoid too much overlap)
        selected = []
        used_games = set()
        
        for parlay in scored_parlays:
            parlay_games = {l['game'].id for l in parlay['legs']}
            overlap = len(parlay_games & used_games)
            
            # Prefer parlays with less overlap
            if overlap < len(parlay_games) * 0.5 or len(selected) < max_parlays:
                selected.append(parlay)
                used_games.update(parlay_games)
                
                if len(selected) >= max_parlays:
                    break
        
        return selected


class PortfolioOptimizer:
    """Portfolio optimization for multiple parlays."""
    
    def __init__(self, bankroll: float = 1000.0):
        self.bankroll = bankroll
        self.kelly = KellyCriterion()
    
    def calculate_portfolio_ev(self, parlays: List[Dict], stakes: List[float]) -> float:
        """Calculate expected value of a portfolio."""
        total_ev = 0.0
        
        for parlay, stake in zip(parlays, stakes):
            ev = parlay.get('expected_value', 0.0)
            total_ev += ev * stake
        
        return total_ev
    
    def calculate_portfolio_variance(self, parlays: List[Dict], stakes: List[float]) -> float:
        """Calculate variance of portfolio returns."""
        # Simplified variance calculation
        # In reality, would need covariance matrix
        variance = 0.0
        
        for parlay, stake in zip(parlays, stakes):
            prob = parlay.get('implied_probability', 0.0)
            odds = parlay.get('combined_odds', 0.0)
            
            # Convert to decimal
            if odds < 0:
                decimal_odds = (100 / abs(odds)) + 1
            else:
                decimal_odds = (odds / 100) + 1
            
            # Variance = p(1-p) * (stake * odds)^2
            variance += prob * (1 - prob) * (stake * decimal_odds) ** 2
        
        return variance
    
    def optimize_stakes(self, parlays: List[Dict], max_total_stake: float = None) -> List[float]:
        """Optimize stake allocation across parlays."""
        if max_total_stake is None:
            max_total_stake = self.bankroll * 0.1  # Max 10% of bankroll
        
        n = len(parlays)
        if n == 0:
            return []
        
        # Use Kelly Criterion for each parlay
        stakes = []
        for parlay in parlays:
            # Estimate true probability (use confidence score as proxy)
            true_prob = parlay.get('confidence_score', 0.5)
            kelly_fraction = self.kelly.calculate_kelly_fraction(
                true_prob,
                parlay['combined_odds'],
                self.bankroll
            )
            stake = self.bankroll * kelly_fraction
            stakes.append(stake)
        
        # Normalize to max_total_stake
        total = sum(stakes)
        if total > max_total_stake:
            stakes = [s * (max_total_stake / total) for s in stakes]
        
        return stakes
    
    def calculate_sharpe_ratio(self, parlays: List[Dict], stakes: List[float]) -> float:
        """Calculate Sharpe ratio for portfolio."""
        ev = self.calculate_portfolio_ev(parlays, stakes)
        variance = self.calculate_portfolio_variance(parlays, stakes)
        std_dev = np.sqrt(variance)
        
        if std_dev == 0:
            return 0.0
        
        # Sharpe ratio = (Expected Return - Risk Free Rate) / Std Dev
        # Assuming risk-free rate = 0 for betting
        return ev / std_dev


class RiskManager:
    """Risk management and bankroll protection."""
    
    def __init__(self, bankroll: float = 1000.0, max_daily_risk: float = 0.05):
        self.bankroll = bankroll
        self.max_daily_risk = max_daily_risk  # Max 5% of bankroll per day
        self.daily_stake = 0.0
    
    def can_place_bet(self, stake: float) -> bool:
        """Check if bet can be placed within risk limits."""
        if self.daily_stake + stake > self.bankroll * self.max_daily_risk:
            return False
        return True
    
    def record_bet(self, stake: float):
        """Record a bet placement."""
        self.daily_stake += stake
    
    def reset_daily(self):
        """Reset daily tracking."""
        self.daily_stake = 0.0
    
    def calculate_max_stake(self, parlay: Dict) -> float:
        """Calculate maximum stake for a parlay based on risk limits."""
        remaining = (self.bankroll * self.max_daily_risk) - self.daily_stake
        return max(0.0, remaining)
    
    def check_drawdown(self, current_bankroll: float, peak_bankroll: float) -> Tuple[bool, float]:
        """Check for significant drawdown."""
        if peak_bankroll == 0:
            return True, 0.0
        
        drawdown = (peak_bankroll - current_bankroll) / peak_bankroll
        max_drawdown = 0.20  # 20% max drawdown
        
        return drawdown < max_drawdown, drawdown


class AdvancedMetrics:
    """Advanced performance metrics."""
    
    @staticmethod
    def calculate_roi_by_sport(parlays: List[Parlay]) -> Dict[str, float]:
        """Calculate ROI broken down by sport."""
        sport_roi = {}
        
        for parlay in parlays:
            if parlay.result not in ['win', 'loss']:
                continue
            
            sport = parlay.sport or 'Unknown'
            if sport not in sport_roi:
                sport_roi[sport] = {'stake': 0.0, 'payout': 0.0}
            
            sport_roi[sport]['stake'] += parlay.stake
            sport_roi[sport]['payout'] += parlay.payout or 0.0
        
        # Calculate ROI for each sport
        result = {}
        for sport, data in sport_roi.items():
            if data['stake'] > 0:
                result[sport] = ((data['payout'] - data['stake']) / data['stake']) * 100
            else:
                result[sport] = 0.0
        
        return result
    
    @staticmethod
    def calculate_confidence_accuracy(parlays: List[Parlay]) -> Dict[str, float]:
        """Calculate accuracy by confidence rating."""
        confidence_stats = {
            'High': {'wins': 0, 'total': 0},
            'Moderate': {'wins': 0, 'total': 0},
            'Low': {'wins': 0, 'total': 0}
        }
        
        for parlay in parlays:
            if parlay.result not in ['win', 'loss']:
                continue
            
            rating = parlay.confidence_rating
            if rating in confidence_stats:
                confidence_stats[rating]['total'] += 1
                if parlay.result == 'win':
                    confidence_stats[rating]['wins'] += 1
        
        # Calculate accuracy
        accuracy = {}
        for rating, stats in confidence_stats.items():
            if stats['total'] > 0:
                accuracy[rating] = stats['wins'] / stats['total']
            else:
                accuracy[rating] = 0.0
        
        return accuracy
    
    @staticmethod
    def calculate_parlay_size_performance(parlays: List[Parlay]) -> Dict[int, Dict]:
        """Analyze performance by parlay size (number of legs)."""
        size_stats = {}
        
        for parlay in parlays:
            if parlay.result not in ['win', 'loss']:
                continue
            
            # Count legs
            from models import Leg
            session = SessionLocal()
            leg_count = session.query(Leg).filter_by(parlay_id=parlay.id).count()
            session.close()
            
            if leg_count not in size_stats:
                size_stats[leg_count] = {'wins': 0, 'losses': 0, 'stake': 0.0, 'payout': 0.0}
            
            size_stats[leg_count]['stake'] += parlay.stake
            size_stats[leg_count]['payout'] += parlay.payout or 0.0
            
            if parlay.result == 'win':
                size_stats[leg_count]['wins'] += 1
            else:
                size_stats[leg_count]['losses'] += 1
        
        # Calculate metrics
        result = {}
        for size, stats in size_stats.items():
            total = stats['wins'] + stats['losses']
            result[size] = {
                'hit_rate': stats['wins'] / total if total > 0 else 0.0,
                'roi': ((stats['payout'] - stats['stake']) / stats['stake'] * 100) if stats['stake'] > 0 else 0.0,
                'total': total
            }
        
        return result

