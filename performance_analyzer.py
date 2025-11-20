"""Performance breakdowns and analytics."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Parlay, Leg, Game, SessionLocal
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """Analyze performance by various dimensions."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def get_performance_by_sport(self, days: int = 30) -> Dict:
        """Get performance breakdown by sport."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        parlays = self.session.query(Parlay).filter(
            Parlay.created_at >= cutoff,
            Parlay.result.in_(["win", "loss"])
        ).all()
        
        sport_stats = {}
        
        for parlay in parlays:
            # Get sport from legs
            legs = parlay.legs
            if not legs:
                continue
            
            sport = legs[0].game.sport
            if sport not in sport_stats:
                sport_stats[sport] = {
                    "total": 0,
                    "wins": 0,
                    "losses": 0,
                    "stake": 0.0,
                    "payout": 0.0
                }
            
            sport_stats[sport]["total"] += 1
            if parlay.result == "win":
                sport_stats[sport]["wins"] += 1
                sport_stats[sport]["payout"] += parlay.payout or 0
            else:
                sport_stats[sport]["losses"] += 1
            sport_stats[sport]["stake"] += parlay.stake or 0
        
        # Calculate metrics
        for sport, stats in sport_stats.items():
            stats["hit_rate"] = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
            stats["profit"] = stats["payout"] - stats["stake"]
            stats["roi"] = (stats["profit"] / stats["stake"] * 100) if stats["stake"] > 0 else 0
        
        return sport_stats
    
    def get_performance_by_bet_type(self, days: int = 30) -> Dict:
        """Get performance breakdown by bet type."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        legs = self.session.query(Leg).join(Parlay).filter(
            Parlay.created_at >= cutoff,
            Leg.result.in_(["win", "loss"])
        ).all()
        
        type_stats = {}
        
        for leg in legs:
            bet_type = leg.bet_type
            if bet_type not in type_stats:
                type_stats[bet_type] = {
                    "total": 0,
                    "wins": 0,
                    "losses": 0
                }
            
            type_stats[bet_type]["total"] += 1
            if leg.result == "win":
                type_stats[bet_type]["wins"] += 1
            else:
                type_stats[bet_type]["losses"] += 1
        
        # Calculate hit rates
        for bet_type, stats in type_stats.items():
            stats["hit_rate"] = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
        
        return type_stats
    
    def get_performance_by_confidence(self, days: int = 30) -> Dict:
        """Get performance breakdown by confidence level."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        parlays = self.session.query(Parlay).filter(
            Parlay.created_at >= cutoff,
            Parlay.result.in_(["win", "loss"])
        ).all()
        
        conf_stats = {
            "High": {"total": 0, "wins": 0, "losses": 0, "stake": 0.0, "payout": 0.0},
            "Moderate": {"total": 0, "wins": 0, "losses": 0, "stake": 0.0, "payout": 0.0},
            "Low": {"total": 0, "wins": 0, "losses": 0, "stake": 0.0, "payout": 0.0}
        }
        
        for parlay in parlays:
            conf = parlay.confidence_rating or "Low"
            if conf not in conf_stats:
                conf = "Low"
            
            conf_stats[conf]["total"] += 1
            if parlay.result == "win":
                conf_stats[conf]["wins"] += 1
                conf_stats[conf]["payout"] += parlay.payout or 0
            else:
                conf_stats[conf]["losses"] += 1
            conf_stats[conf]["stake"] += parlay.stake or 0
        
        # Calculate metrics
        for conf, stats in conf_stats.items():
            stats["hit_rate"] = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
            stats["profit"] = stats["payout"] - stats["stake"]
            stats["roi"] = (stats["profit"] / stats["stake"] * 100) if stats["stake"] > 0 else 0
        
        return conf_stats
    
    def get_performance_by_day_of_week(self, days: int = 30) -> Dict:
        """Get performance by day of week."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        parlays = self.session.query(Parlay).filter(
            Parlay.created_at >= cutoff,
            Parlay.result.in_(["win", "loss"])
        ).all()
        
        day_stats = {}
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for day in days_of_week:
            day_stats[day] = {"total": 0, "wins": 0, "losses": 0, "stake": 0.0, "payout": 0.0}
        
        for parlay in parlays:
            day = parlay.created_at.strftime("%A")
            if day not in day_stats:
                continue
            
            day_stats[day]["total"] += 1
            if parlay.result == "win":
                day_stats[day]["wins"] += 1
                day_stats[day]["payout"] += parlay.payout or 0
            else:
                day_stats[day]["losses"] += 1
            day_stats[day]["stake"] += parlay.stake or 0
        
        # Calculate metrics
        for day, stats in day_stats.items():
            stats["hit_rate"] = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
            stats["profit"] = stats["payout"] - stats["stake"]
            stats["roi"] = (stats["profit"] / stats["stake"] * 100) if stats["stake"] > 0 else 0
        
        return day_stats
    
    def get_closing_line_value_stats(self) -> Dict:
        """Get CLV statistics."""
        from models import ClosingLineValue
        
        clv_records = self.session.query(ClosingLineValue).all()
        
        if not clv_records:
            return {}
        
        total = len(clv_records)
        beat_closing = sum(1 for c in clv_records if c.beat_closing_line)
        avg_clv = sum(c.clv_percentage for c in clv_records) / total if total > 0 else 0
        
        return {
            "total_bets": total,
            "beat_closing_line": beat_closing,
            "beat_closing_rate": beat_closing / total if total > 0 else 0,
            "average_clv": avg_clv,
            "sharp_indicator": sum(c.sharp_indicator for c in clv_records) / total if total > 0 else 0
        }
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

