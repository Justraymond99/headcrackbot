"""Result tracker for updating bet outcomes and calculating ROI."""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from models import Game, Leg, Parlay, DailyReport, SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResultTracker:
    """Track bet results and calculate performance metrics."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def update_game_result(self, game_id: int, home_score: int, away_score: int):
        """Update game result and determine leg outcomes."""
        game = self.session.query(Game).filter_by(id=game_id).first()
        if not game:
            logger.error(f"Game {game_id} not found")
            return
        
        game.status = "finished"
        
        # Update all legs for this game
        legs = self.session.query(Leg).filter_by(game_id=game_id).all()
        
        for leg in legs:
            if leg.result != "pending":
                continue  # Already updated
            
            outcome = self._determine_leg_outcome(leg, game, home_score, away_score)
            leg.result = outcome["result"]
            leg.actual_outcome = outcome["actual_outcome"]
            leg.updated_at = datetime.utcnow()
        
        self.session.commit()
        logger.info(f"Updated results for game {game_id}")
    
    def _determine_leg_outcome(self, leg: Leg, game: Game, home_score: int, away_score: int) -> Dict:
        """Determine if a leg won or lost."""
        if leg.bet_type == "moneyline":
            if leg.selection == game.home_team:
                if home_score > away_score:
                    return {"result": "win", "actual_outcome": f"{game.home_team} won {home_score}-{away_score}"}
                else:
                    return {"result": "loss", "actual_outcome": f"{game.away_team} won {away_score}-{home_score}"}
            else:  # away team
                if away_score > home_score:
                    return {"result": "win", "actual_outcome": f"{game.away_team} won {away_score}-{home_score}"}
                else:
                    return {"result": "loss", "actual_outcome": f"{game.home_team} won {home_score}-{away_score}"}
        
        elif leg.bet_type == "spread":
            # Parse spread (e.g., "Lakers -3.5")
            spread_value = float(leg.selection.split()[-1])
            team = " ".join(leg.selection.split()[:-1])
            
            if team == game.home_team:
                adjusted_home = home_score + spread_value
                if adjusted_home > away_score:
                    return {"result": "win", "actual_outcome": f"{game.home_team} covered"}
                elif adjusted_home == away_score:
                    return {"result": "push", "actual_outcome": "Push"}
                else:
                    return {"result": "loss", "actual_outcome": f"{game.home_team} did not cover"}
            else:
                adjusted_away = away_score + abs(spread_value)
                if adjusted_away > home_score:
                    return {"result": "win", "actual_outcome": f"{game.away_team} covered"}
                elif adjusted_away == home_score:
                    return {"result": "push", "actual_outcome": "Push"}
                else:
                    return {"result": "loss", "actual_outcome": f"{game.away_team} did not cover"}
        
        elif leg.bet_type == "total":
            total_points = home_score + away_score
            total_line = float(leg.selection.split()[-1])
            
            if "Over" in leg.selection:
                if total_points > total_line:
                    return {"result": "win", "actual_outcome": f"Over {total_points} points"}
                elif total_points == total_line:
                    return {"result": "push", "actual_outcome": "Push"}
                else:
                    return {"result": "loss", "actual_outcome": f"Under {total_points} points"}
            else:  # Under
                if total_points < total_line:
                    return {"result": "win", "actual_outcome": f"Under {total_points} points"}
                elif total_points == total_line:
                    return {"result": "push", "actual_outcome": "Push"}
                else:
                    return {"result": "loss", "actual_outcome": f"Over {total_points} points"}
        
        return {"result": "pending", "actual_outcome": "Unknown"}
    
    def update_parlay_result(self, parlay_id: int):
        """Update parlay result based on leg outcomes."""
        parlay = self.session.query(Parlay).filter_by(id=parlay_id).first()
        if not parlay:
            return
        
        legs = self.session.query(Leg).filter_by(parlay_id=parlay_id).all()
        
        # Check if all legs are resolved
        if all(leg.result != "pending" for leg in legs):
            # Determine parlay result
            if all(leg.result == "win" for leg in legs):
                parlay.result = "win"
                # Calculate payout
                decimal_odds = self._american_to_decimal(parlay.combined_odds)
                parlay.payout = parlay.stake * decimal_odds
            elif any(leg.result == "loss" for leg in legs):
                parlay.result = "loss"
                parlay.payout = 0.0
            else:
                # Handle pushes (could adjust odds)
                parlay.result = "push"
                parlay.payout = parlay.stake
            
            parlay.status = "finished"
            parlay.updated_at = datetime.utcnow()
            self.session.commit()
            logger.info(f"Updated parlay {parlay_id}: {parlay.result}")
    
    def _american_to_decimal(self, american_odds: float) -> float:
        """Convert American odds to decimal."""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
    
    def calculate_hit_rate(self, parlays: List[Parlay]) -> float:
        """Calculate hit rate (win percentage)."""
        finished = [p for p in parlays if p.result in ["win", "loss"]]
        if not finished:
            return 0.0
        
        wins = sum(1 for p in finished if p.result == "win")
        return wins / len(finished)
    
    def calculate_roi(self, parlays: List[Parlay]) -> float:
        """Calculate ROI percentage."""
        finished = [p for p in parlays if p.result in ["win", "loss"]]
        if not finished:
            return 0.0
        
        total_stake = sum(p.stake for p in finished)
        total_payout = sum(p.payout or 0 for p in finished)
        
        if total_stake == 0:
            return 0.0
        
        return ((total_payout - total_stake) / total_stake) * 100
    
    def generate_daily_report(self, date: Optional[datetime] = None) -> DailyReport:
        """Generate daily performance report."""
        if date is None:
            date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check if report already exists
        existing = self.session.query(DailyReport).filter_by(report_date=date).first()
        if existing:
            return existing
        
        # Get all parlays for the day
        start_date = date
        end_date = date + timedelta(days=1)
        
        parlays = self.session.query(Parlay).filter(
            Parlay.created_at >= start_date,
            Parlay.created_at < end_date
        ).all()
        
        locked_parlays = [p for p in parlays if p.locked]
        finished_parlays = [p for p in locked_parlays if p.result in ["win", "loss"]]
        
        wins = sum(1 for p in finished_parlays if p.result == "win")
        losses = sum(1 for p in finished_parlays if p.result == "loss")
        hit_rate = self.calculate_hit_rate(locked_parlays) if locked_parlays else 0.0
        roi = self.calculate_roi(locked_parlays) if locked_parlays else 0.0
        
        total_stake = sum(p.stake for p in locked_parlays)
        total_payout = sum(p.payout or 0 for p in finished_parlays)
        
        report = DailyReport(
            report_date=date,
            total_parlays=len(parlays),
            locked_parlays=len(locked_parlays),
            wins=wins,
            losses=losses,
            hit_rate=hit_rate,
            roi=roi,
            total_stake=total_stake,
            total_payout=total_payout
        )
        
        self.session.add(report)
        self.session.commit()
        logger.info(f"Generated daily report for {date.date()}")
        return report
    
    def get_performance_trends(self, days: int = 30) -> pd.DataFrame:
        """Get performance trends over time."""
        start_date = datetime.now() - timedelta(days=days)
        
        reports = self.session.query(DailyReport).filter(
            DailyReport.report_date >= start_date
        ).order_by(DailyReport.report_date).all()
        
        data = []
        for report in reports:
            data.append({
                "date": report.report_date,
                "hit_rate": report.hit_rate or 0.0,
                "roi": report.roi or 0.0,
                "wins": report.wins,
                "losses": report.losses,
                "total_parlays": report.total_parlays
            })
        
        return pd.DataFrame(data)
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

