"""Backtesting framework for strategy validation."""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from models import Game, Parlay, Leg, SessionLocal
from research_engine import ResearchEngine
from result_tracker import ResultTracker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Backtester:
    """Backtest betting strategies on historical data."""
    
    def __init__(self, initial_bankroll: float = 1000.0):
        self.initial_bankroll = initial_bankroll
        self.bankroll = initial_bankroll
        self.engine = ResearchEngine()
        self.tracker = ResultTracker()
        self.session = SessionLocal()
    
    def simulate_period(
        self,
        start_date: datetime,
        end_date: datetime,
        strategy: str = "kelly",
        max_parlays_per_day: int = 5
    ) -> Dict:
        """
        Simulate betting over a time period.
        
        Args:
            start_date: Start of backtest period
            end_date: End of backtest period
            strategy: Betting strategy ('kelly', 'fixed', 'proportional')
            max_parlays_per_day: Maximum parlays to place per day
        
        Returns:
            Dictionary with backtest results
        """
        current_date = start_date
        results = []
        peak_bankroll = self.bankroll
        
        while current_date <= end_date:
            # Get games for this date
            games = self.session.query(Game).filter(
                Game.game_date >= current_date,
                Game.game_date < current_date + timedelta(days=1),
                Game.status == "scheduled"
            ).all()
            
            if games:
                # Generate parlays
                parlays = self.engine.generate_parlays(games, max_parlays_per_day)
                
                # Select parlays based on strategy
                selected = self._select_parlays(parlays, strategy)
                
                # Place bets
                for parlay_data in selected:
                    stake = self._calculate_stake(parlay_data, strategy)
                    
                    if stake > 0 and stake <= self.bankroll * 0.1:  # Max 10% per bet
                        # Simulate outcome
                        outcome = self._simulate_outcome(parlay_data)
                        payout = 0
                        
                        if outcome == 'win':
                            # Calculate payout
                            if parlay_data['combined_odds'] < 0:
                                decimal_odds = (100 / abs(parlay_data['combined_odds'])) + 1
                            else:
                                decimal_odds = (parlay_data['combined_odds'] / 100) + 1
                            
                            payout = stake * decimal_odds
                            self.bankroll += (payout - stake)
                        else:
                            self.bankroll -= stake
                        
                        results.append({
                            'date': current_date,
                            'stake': stake,
                            'payout': payout,
                            'result': outcome,
                            'bankroll': self.bankroll
                        })
                        
                        peak_bankroll = max(peak_bankroll, self.bankroll)
            
            current_date += timedelta(days=1)
        
        # Calculate metrics
        total_stake = sum(r['stake'] for r in results)
        total_payout = sum(r['payout'] for r in results)
        wins = sum(1 for r in results if r['result'] == 'win')
        losses = sum(1 for r in results if r['result'] == 'loss')
        
        roi = ((total_payout - total_stake) / total_stake * 100) if total_stake > 0 else 0
        hit_rate = wins / (wins + losses) if (wins + losses) > 0 else 0
        profit = self.bankroll - self.initial_bankroll
        drawdown = (peak_bankroll - self.bankroll) / peak_bankroll if peak_bankroll > 0 else 0
        
        return {
            'initial_bankroll': self.initial_bankroll,
            'final_bankroll': self.bankroll,
            'profit': profit,
            'roi': roi,
            'hit_rate': hit_rate,
            'total_bets': len(results),
            'wins': wins,
            'losses': losses,
            'total_stake': total_stake,
            'total_payout': total_payout,
            'max_drawdown': drawdown,
            'results': results
        }
    
    def _select_parlays(self, parlays: List[Dict], strategy: str) -> List[Dict]:
        """Select parlays based on strategy."""
        if not parlays:
            return []
        
        if strategy == "kelly":
            # Select top EV parlays
            return sorted(parlays, key=lambda x: x.get('expected_value', 0), reverse=True)[:5]
        elif strategy == "conservative":
            # Select only high confidence
            return [p for p in parlays if p.get('confidence_rating') == 'High'][:3]
        else:
            # Default: top by score
            return sorted(parlays, key=lambda x: x.get('score', 0), reverse=True)[:5]
    
    def _calculate_stake(self, parlay: Dict, strategy: str) -> float:
        """Calculate stake based on strategy."""
        if strategy == "kelly":
            from advanced_analytics import KellyCriterion
            kelly = KellyCriterion()
            true_prob = parlay.get('confidence_score', 0.5)
            fraction = kelly.calculate_kelly_fraction(
                true_prob,
                parlay['combined_odds'],
                self.bankroll
            )
            return self.bankroll * fraction
        elif strategy == "fixed":
            return 10.0  # Fixed $10 per bet
        else:  # proportional
            return self.bankroll * 0.01  # 1% of bankroll
    
    def _simulate_outcome(self, parlay: Dict) -> str:
        """Simulate parlay outcome based on probabilities."""
        # Use implied probability to simulate
        prob = parlay.get('implied_probability', 0.5)
        return 'win' if np.random.random() < prob else 'loss'
    
    def compare_strategies(
        self,
        start_date: datetime,
        end_date: datetime,
        strategies: List[str] = None
    ) -> pd.DataFrame:
        """Compare multiple strategies."""
        if strategies is None:
            strategies = ['kelly', 'fixed', 'proportional']
        
        results = []
        for strategy in strategies:
            # Reset bankroll for each strategy
            self.bankroll = self.initial_bankroll
            
            result = self.simulate_period(start_date, end_date, strategy)
            result['strategy'] = strategy
            results.append(result)
        
        return pd.DataFrame(results)
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

