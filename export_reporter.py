"""Export and reporting functionality."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Parlay, Leg, DailyReport, SessionLocal
import pandas as pd
import json
import logging

logger = logging.getLogger(__name__)


class ExportReporter:
    """Handle exports and reports."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def export_to_csv(self, start_date: datetime, end_date: datetime, filepath: str):
        """Export parlays to CSV."""
        parlays = self.session.query(Parlay).filter(
            Parlay.created_at >= start_date,
            Parlay.created_at <= end_date
        ).all()
        
        data = []
        for parlay in parlays:
            data.append({
                "ID": parlay.id,
                "Name": parlay.name,
                "Sport": parlay.sport,
                "Date": parlay.created_at.strftime("%Y-%m-%d"),
                "Odds": parlay.combined_odds,
                "Stake": parlay.stake,
                "Payout": parlay.payout,
                "Result": parlay.result,
                "ROI": ((parlay.payout - parlay.stake) / parlay.stake * 100) if parlay.stake else 0,
                "Confidence": parlay.confidence_rating
            })
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        logger.info(f"Exported {len(data)} parlays to {filepath}")
    
    def export_to_excel(self, start_date: datetime, end_date: datetime, filepath: str):
        """Export to Excel with multiple sheets."""
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Parlays sheet
            parlays = self.session.query(Parlay).filter(
                Parlay.created_at >= start_date,
                Parlay.created_at <= end_date
            ).all()
            
            parlay_data = []
            for parlay in parlays:
                parlay_data.append({
                    "ID": parlay.id,
                    "Name": parlay.name,
                    "Sport": parlay.sport,
                    "Date": parlay.created_at.strftime("%Y-%m-%d %H:%M"),
                    "Odds": parlay.combined_odds,
                    "Stake": parlay.stake,
                    "Payout": parlay.payout or 0,
                    "Profit": (parlay.payout or 0) - parlay.stake,
                    "Result": parlay.result,
                    "Confidence": parlay.confidence_rating
                })
            
            df_parlays = pd.DataFrame(parlay_data)
            df_parlays.to_excel(writer, sheet_name="Parlays", index=False)
            
            # Legs sheet
            legs = self.session.query(Leg).join(Parlay).filter(
                Parlay.created_at >= start_date,
                Parlay.created_at <= end_date
            ).all()
            
            leg_data = []
            for leg in legs:
                leg_data.append({
                    "Parlay ID": leg.parlay_id,
                    "Game": f"{leg.game.away_team or leg.game.fighter2} @ {leg.game.home_team or leg.game.fighter1}",
                    "Bet Type": leg.bet_type,
                    "Selection": leg.selection,
                    "Odds": leg.odds,
                    "Result": leg.result
                })
            
            df_legs = pd.DataFrame(leg_data)
            df_legs.to_excel(writer, sheet_name="Legs", index=False)
            
            # Summary sheet
            summary_data = self._calculate_summary(start_date, end_date)
            df_summary = pd.DataFrame([summary_data])
            df_summary.to_excel(writer, sheet_name="Summary", index=False)
        
        logger.info(f"Exported to Excel: {filepath}")
    
    def generate_tax_report(self, year: int, filepath: str):
        """Generate tax report (win/loss statement)."""
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)
        
        parlays = self.session.query(Parlay).filter(
            Parlay.created_at >= start_date,
            Parlay.created_at <= end_date,
            Parlay.result.in_(["win", "loss"])
        ).all()
        
        wins = [p for p in parlays if p.result == "win"]
        losses = [p for p in parlays if p.result == "loss"]
        
        total_wagered = sum(p.stake for p in parlays)
        total_won = sum(p.payout or 0 for p in wins)
        total_lost = sum(p.stake for p in losses)
        net_gain = total_won - total_wagered
        
        report = {
            "Year": year,
            "Total Wagers": total_wagered,
            "Total Won": total_won,
            "Total Lost": total_lost,
            "Net Gain/Loss": net_gain,
            "Wins": len(wins),
            "Losses": len(losses),
            "Win Rate": len(wins) / len(parlays) * 100 if parlays else 0
        }
        
        df = pd.DataFrame([report])
        df.to_csv(filepath, index=False)
        logger.info(f"Tax report generated: {filepath}")
        return report
    
    def _calculate_summary(self, start_date: datetime, end_date: datetime) -> Dict:
        """Calculate summary statistics."""
        parlays = self.session.query(Parlay).filter(
            Parlay.created_at >= start_date,
            Parlay.created_at <= end_date,
            Parlay.result.in_(["win", "loss"])
        ).all()
        
        if not parlays:
            return {}
        
        wins = [p for p in parlays if p.result == "win"]
        total_stake = sum(p.stake for p in parlays)
        total_payout = sum(p.payout or 0 for p in wins)
        profit = total_payout - total_stake
        roi = (profit / total_stake * 100) if total_stake > 0 else 0
        
        return {
            "Total Parlays": len(parlays),
            "Wins": len(wins),
            "Losses": len(parlays) - len(wins),
            "Hit Rate": len(wins) / len(parlays) * 100,
            "Total Stake": total_stake,
            "Total Payout": total_payout,
            "Profit": profit,
            "ROI": roi
        }
    
    def export_to_json(self, start_date: datetime, end_date: datetime, filepath: str):
        """Export to JSON format."""
        parlays = self.session.query(Parlay).filter(
            Parlay.created_at >= start_date,
            Parlay.created_at <= end_date
        ).all()
        
        data = {
            "export_date": datetime.now().isoformat(),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "parlays": []
        }
        
        for parlay in parlays:
            parlay_data = {
                "id": parlay.id,
                "name": parlay.name,
                "sport": parlay.sport,
                "created_at": parlay.created_at.isoformat(),
                "odds": parlay.combined_odds,
                "stake": parlay.stake,
                "payout": parlay.payout,
                "result": parlay.result,
                "legs": []
            }
            
            for leg in parlay.legs:
                leg_data = {
                    "bet_type": leg.bet_type,
                    "selection": leg.selection,
                    "odds": leg.odds,
                    "result": leg.result
                }
                parlay_data["legs"].append(leg_data)
            
            data["parlays"].append(parlay_data)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported to JSON: {filepath}")
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

