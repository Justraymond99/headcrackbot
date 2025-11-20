"""Reinforcement learning for adaptive bet sizing."""
from typing import Dict, List
from models import Parlay, SessionLocal
from bankroll_manager import BankrollManager
import numpy as np
import logging

logger = logging.getLogger(__name__)


class ReinforcementLearning:
    """Reinforcement learning for optimal bet sizing."""
    
    def __init__(self, user_id: str = "default"):
        self.session = SessionLocal()
        self.user_id = user_id
        self.bankroll_manager = BankrollManager(user_id)
        
        # Q-learning parameters
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.epsilon = 0.1  # Exploration rate
        
        # State-action values (simplified)
        self.q_table = {}  # Would store state-action values
    
    def get_optimal_stake(
        self,
        parlay_odds: float,
        true_probability: float,
        confidence: float,
        bankroll: float
    ) -> float:
        """Get optimal stake using RL."""
        # State: (odds_range, confidence_range, bankroll_pct)
        # Action: stake percentage
        
        # Simplified RL approach
        # In production, would use proper Q-learning with state space
        
        # Base stake from Kelly
        kelly_stake = self.bankroll_manager.calculate_kelly_stake(
            parlay_odds, true_probability
        )
        
        # Adjust based on confidence
        adjusted_stake = kelly_stake * confidence
        
        # Apply exploration (epsilon-greedy)
        if np.random.random() < self.epsilon:
            # Explore: use slightly different stake
            exploration_factor = np.random.uniform(0.8, 1.2)
            adjusted_stake *= exploration_factor
        
        return max(0, min(adjusted_stake, bankroll * 0.1))  # Cap at 10% of bankroll
    
    def update_from_result(self, parlay: Parlay, result: str):
        """Update Q-values based on result."""
        # In real RL, would update Q-table based on reward
        # Reward = profit if win, -stake if loss
        
        if result == "win":
            reward = (parlay.payout or 0) - parlay.stake
        else:
            reward = -parlay.stake
        
        # Update Q-values (simplified)
        # In production, would properly update state-action values
        logger.debug(f"RL update: reward={reward}, parlay={parlay.id}")
    
    def get_policy(self) -> Dict:
        """Get current policy."""
        return {
            "learning_rate": self.learning_rate,
            "discount_factor": self.discount_factor,
            "epsilon": self.epsilon,
            "states_explored": len(self.q_table)
        }
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

