"""Bankroll management system."""
from typing import Dict, Optional
from datetime import datetime, timedelta
from models import Bankroll, Parlay, Leg, SessionLocal
from advanced_analytics import KellyCriterion
import logging

logger = logging.getLogger(__name__)


class BankrollManager:
    """Manage bankroll, unit sizing, and betting limits."""
    
    def __init__(self, user_id: str = "default"):
        self.session = SessionLocal()
        self.user_id = user_id
        self.kelly = KellyCriterion()
        self._ensure_bankroll_exists()
    
    def _ensure_bankroll_exists(self):
        """Create bankroll if it doesn't exist."""
        bankroll = self.session.query(Bankroll).filter_by(user_id=self.user_id).first()
        if not bankroll:
            bankroll = Bankroll(
                user_id=self.user_id,
                current_balance=1000.0,
                starting_balance=1000.0
            )
            self.session.add(bankroll)
            self.session.commit()
    
    def get_bankroll(self) -> Bankroll:
        """Get current bankroll."""
        return self.session.query(Bankroll).filter_by(user_id=self.user_id).first()
    
    def update_balance(self, amount: float, transaction_type: str = "bet"):
        """Update bankroll balance."""
        bankroll = self.get_bankroll()
        if transaction_type == "deposit":
            bankroll.current_balance += amount
            bankroll.total_deposits += amount
        elif transaction_type == "withdrawal":
            bankroll.current_balance -= amount
            bankroll.total_withdrawals += amount
        elif transaction_type == "win":
            bankroll.current_balance += amount
        elif transaction_type == "loss":
            bankroll.current_balance -= amount
        
        bankroll.updated_at = datetime.utcnow()
        self.session.commit()
    
    def calculate_unit_size(self, confidence: float = 1.0) -> float:
        """Calculate recommended unit size based on bankroll."""
        bankroll = self.get_bankroll()
        base_unit = bankroll.current_balance * (bankroll.base_unit_size / 100.0)
        return base_unit * confidence
    
    def calculate_kelly_stake(self, parlay_odds: float, true_probability: float) -> float:
        """Calculate stake using Kelly Criterion."""
        bankroll = self.get_bankroll()
        kelly_fraction = bankroll.kelly_fraction or 0.25
        
        # Calculate full Kelly
        full_kelly = self.kelly.calculate_parlay_kelly(
            Parlay(combined_odds=parlay_odds),
            [true_probability]
        )
        
        # Apply fractional Kelly
        stake = bankroll.current_balance * full_kelly * kelly_fraction
        return max(0, min(stake, bankroll.max_bet_size or stake))
    
    def check_budget_limits(self, stake: float) -> Dict[str, bool]:
        """Check if stake is within budget limits."""
        bankroll = self.get_bankroll()
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Reset daily/weekly/monthly if needed
        if bankroll.updated_at.date() < today:
            bankroll.daily_stake = 0.0
        if bankroll.updated_at.date() < week_start:
            bankroll.weekly_stake = 0.0
        if bankroll.updated_at.month < month_start.month:
            bankroll.monthly_stake = 0.0
        
        checks = {
            "daily_ok": True,
            "weekly_ok": True,
            "monthly_ok": True,
            "max_bet_ok": True,
            "max_parlay_ok": True
        }
        
        if bankroll.daily_budget:
            checks["daily_ok"] = (bankroll.daily_stake + stake) <= bankroll.daily_budget
        if bankroll.weekly_budget:
            checks["weekly_ok"] = (bankroll.weekly_stake + stake) <= bankroll.weekly_budget
        if bankroll.monthly_budget:
            checks["monthly_ok"] = (bankroll.monthly_stake + stake) <= bankroll.monthly_budget
        if bankroll.max_bet_size:
            checks["max_bet_ok"] = stake <= bankroll.max_bet_size
        if bankroll.max_parlay_stake:
            checks["max_parlay_ok"] = stake <= bankroll.max_parlay_stake
        
        return checks
    
    def record_stake(self, stake: float):
        """Record a stake for budget tracking."""
        bankroll = self.get_bankroll()
        bankroll.daily_stake += stake
        bankroll.weekly_stake += stake
        bankroll.monthly_stake += stake
        bankroll.updated_at = datetime.utcnow()
        self.session.commit()
    
    def get_budget_status(self) -> Dict:
        """Get current budget status."""
        bankroll = self.get_bankroll()
        return {
            "current_balance": bankroll.current_balance,
            "starting_balance": bankroll.starting_balance,
            "total_profit": bankroll.current_balance - bankroll.starting_balance,
            "roi": ((bankroll.current_balance - bankroll.starting_balance) / bankroll.starting_balance * 100) if bankroll.starting_balance > 0 else 0,
            "daily_stake": bankroll.daily_stake,
            "daily_budget": bankroll.daily_budget,
            "daily_remaining": (bankroll.daily_budget - bankroll.daily_stake) if bankroll.daily_budget else None,
            "weekly_stake": bankroll.weekly_stake,
            "weekly_budget": bankroll.weekly_budget,
            "weekly_remaining": (bankroll.weekly_budget - bankroll.weekly_stake) if bankroll.weekly_budget else None,
            "monthly_stake": bankroll.monthly_stake,
            "monthly_budget": bankroll.monthly_budget,
            "monthly_remaining": (bankroll.monthly_budget - bankroll.monthly_stake) if bankroll.monthly_budget else None,
        }
    
    def update_settings(self, **kwargs):
        """Update bankroll settings."""
        bankroll = self.get_bankroll()
        for key, value in kwargs.items():
            if hasattr(bankroll, key):
                setattr(bankroll, key, value)
        bankroll.updated_at = datetime.utcnow()
        self.session.commit()
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

