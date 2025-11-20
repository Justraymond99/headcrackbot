"""Historical matchup analyzer."""
from typing import Optional, Dict, List
from datetime import datetime
from models import Game, HistoricalMatchup, SessionLocal
import logging

logger = logging.getLogger(__name__)


class HistoricalMatchupAnalyzer:
    """Analyze historical matchups and head-to-head records."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def get_matchup(self, team1: str, team2: str, sport: str) -> Optional[HistoricalMatchup]:
        """Get historical matchup data."""
        # Try both orderings
        matchup = self.session.query(HistoricalMatchup).filter_by(
            team1=team1,
            team2=team2,
            sport=sport
        ).first()
        
        if not matchup:
            matchup = self.session.query(HistoricalMatchup).filter_by(
                team1=team2,
                team2=team1,
                sport=sport
            ).first()
        
        return matchup
    
    def create_or_update_matchup(
        self,
        team1: str,
        team2: str,
        sport: str,
        team1_wins: int = 0,
        team2_wins: int = 0,
        draws: int = 0,
        last_5_games: Optional[List[Dict]] = None
    ) -> HistoricalMatchup:
        """Create or update matchup record."""
        matchup = self.get_matchup(team1, team2, sport)
        
        if not matchup:
            matchup = HistoricalMatchup(
                team1=team1,
                team2=team2,
                sport=sport
            )
            self.session.add(matchup)
        
        matchup.team1_wins = team1_wins
        matchup.team2_wins = team2_wins
        matchup.draws = draws
        if last_5_games:
            matchup.last_5_games = last_5_games
        
        # Calculate averages from last 5 games
        if last_5_games:
            totals = [g.get("total", 0) for g in last_5_games if g.get("total")]
            margins = [g.get("margin", 0) for g in last_5_games if g.get("margin")]
            
            if totals:
                matchup.avg_total = sum(totals) / len(totals)
            if margins:
                matchup.avg_margin = sum(margins) / len(margins)
        
        matchup.updated_at = datetime.utcnow()
        self.session.commit()
        return matchup
    
    def analyze_matchup(self, game: Game) -> Dict:
        """Analyze historical matchup for a game."""
        if game.sport == "UFC":
            team1 = game.fighter1
            team2 = game.fighter2
        else:
            team1 = game.home_team
            team2 = game.away_team
        
        if not team1 or not team2:
            return {}
        
        matchup = self.get_matchup(team1, team2, game.sport)
        
        if not matchup:
            return {
                "exists": False,
                "message": "No historical data available"
            }
        
        total_games = matchup.team1_wins + matchup.team2_wins + matchup.draws
        
        if total_games == 0:
            return {
                "exists": True,
                "total_games": 0
            }
        
        team1_win_pct = matchup.team1_wins / total_games if total_games > 0 else 0
        team2_win_pct = matchup.team2_wins / total_games if total_games > 0 else 0
        
        # Recent form (last 5 games)
        recent_trend = None
        if matchup.last_5_games:
            recent_wins_team1 = sum(1 for g in matchup.last_5_games if g.get("winner") == team1)
            recent_trend = {
                "team1_recent_wins": recent_wins_team1,
                "team2_recent_wins": len(matchup.last_5_games) - recent_wins_team1,
                "trend": "team1" if recent_wins_team1 > 2 else "team2"
            }
        
        return {
            "exists": True,
            "total_games": total_games,
            "team1_wins": matchup.team1_wins,
            "team2_wins": matchup.team2_wins,
            "draws": matchup.draws,
            "team1_win_pct": team1_win_pct,
            "team2_win_pct": team2_win_pct,
            "avg_total": matchup.avg_total,
            "avg_margin": matchup.avg_margin,
            "recent_trend": recent_trend,
            "last_5_games": matchup.last_5_games
        }
    
    def get_matchup_insights(self, game: Game) -> str:
        """Get text insights from matchup analysis."""
        analysis = self.analyze_matchup(game)
        
        if not analysis.get("exists") or analysis.get("total_games", 0) == 0:
            return "No historical matchup data available."
        
        insights = []
        
        if game.sport == "UFC":
            team1 = game.fighter1
            team2 = game.fighter2
        else:
            team1 = game.home_team
            team2 = game.away_team
        
        # Overall record
        insights.append(
            f"Head-to-Head: {team1} {analysis['team1_wins']}-{analysis['team2_wins']} "
            f"{team2} ({analysis.get('draws', 0)} draws)"
        )
        
        # Win percentage
        if analysis['team1_win_pct'] > 0.6:
            insights.append(f"{team1} has dominated historically ({analysis['team1_win_pct']*100:.0f}% win rate)")
        elif analysis['team2_win_pct'] > 0.6:
            insights.append(f"{team2} has dominated historically ({analysis['team2_win_pct']*100:.0f}% win rate)")
        
        # Recent trend
        if analysis.get("recent_trend"):
            trend = analysis["recent_trend"]
            if trend["trend"] == "team1":
                insights.append(f"{team1} has won {trend['team1_recent_wins']} of last 5 meetings")
            else:
                insights.append(f"{team2} has won {trend['team2_recent_wins']} of last 5 meetings")
        
        # Scoring trends
        if analysis.get("avg_total"):
            insights.append(f"Average total in meetings: {analysis['avg_total']:.1f}")
        
        return " | ".join(insights)
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

