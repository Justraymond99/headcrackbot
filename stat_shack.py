"""Stat Shack - Advanced player and team metrics lookup interface."""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Game, PlayerProp, TeamStat, SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StatShack:
    """Interface for looking up advanced player and team metrics."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def get_player_stats(self, player_name: str, sport: str, days: int = 30) -> Dict:
        """Get comprehensive player statistics."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get player props from recent games
        props = self.session.query(PlayerProp).join(Game).filter(
            PlayerProp.player_name.ilike(f"%{player_name}%"),
            Game.sport == sport,
            Game.game_date >= cutoff_date
        ).all()
        
        stats = {
            "player_name": player_name,
            "sport": sport,
            "games_analyzed": len(set(p.game_id for p in props)),
            "props": {},
            "trends": {},
            "recent_performance": {}
        }
        
        # Analyze by prop type
        prop_types = {}
        for prop in props:
            prop_type = prop.prop_type or prop.market_key
            if prop_type not in prop_types:
                prop_types[prop_type] = []
            prop_types[prop_type].append(prop)
        
        for prop_type, prop_list in prop_types.items():
            if prop.prop_value:  # Over/Under props
                # Calculate average line
                avg_line = np.mean([p.prop_value for p in prop_list if p.prop_value])
                stats["props"][prop_type] = {
                    "count": len(prop_list),
                    "average_line": avg_line,
                    "average_over_odds": np.mean([p.over_odds for p in prop_list if p.over_odds]),
                    "average_under_odds": np.mean([p.under_odds for p in prop_list if p.under_odds])
                }
        
        return stats
    
    def get_team_stats(self, team_name: str, sport: str, days: int = 30) -> Dict:
        """Get comprehensive team statistics."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get team stats from database
        team_stats = self.session.query(TeamStat).filter(
            (TeamStat.team_name.ilike(f"%{team_name}%")),
            TeamStat.sport == sport,
            TeamStat.date >= cutoff_date
        ).all()
        
        # Get games
        games = self.session.query(Game).filter(
            ((Game.home_team.ilike(f"%{team_name}%")) | (Game.away_team.ilike(f"%{team_name}%"))),
            Game.sport == sport,
            Game.game_date >= cutoff_date
        ).all()
        
        stats = {
            "team_name": team_name,
            "sport": sport,
            "games_analyzed": len(games),
            "win_loss": {"wins": 0, "losses": 0},
            "home_record": {"wins": 0, "losses": 0},
            "away_record": {"wins": 0, "losses": 0},
            "average_scores": {},
            "trends": {}
        }
        
        # Calculate win/loss
        for game in games:
            if game.status == "finished":
                is_home = game.home_team and team_name.lower() in game.home_team.lower()
                if is_home:
                    if game.home_score and game.away_score:
                        if game.home_score > game.away_score:
                            stats["win_loss"]["wins"] += 1
                            stats["home_record"]["wins"] += 1
                        else:
                            stats["win_loss"]["losses"] += 1
                            stats["home_record"]["losses"] += 1
                else:
                    if game.home_score and game.away_score:
                        if game.away_score > game.home_score:
                            stats["win_loss"]["wins"] += 1
                            stats["away_record"]["wins"] += 1
                        else:
                            stats["win_loss"]["losses"] += 1
                            stats["away_record"]["losses"] += 1
        
        return stats
    
    def get_head_to_head(self, team1: str, team2: str, sport: str) -> Dict:
        """Get head-to-head statistics between two teams."""
        games = self.session.query(Game).filter(
            Game.sport == sport,
            ((Game.home_team.ilike(f"%{team1}%")) | (Game.away_team.ilike(f"%{team1}%"))),
            ((Game.home_team.ilike(f"%{team2}%")) | (Game.away_team.ilike(f"%{team2}%")))
        ).all()
        
        h2h = {
            "team1": team1,
            "team2": team2,
            "sport": sport,
            "total_games": len(games),
            "team1_wins": 0,
            "team2_wins": 0,
            "recent_games": []
        }
        
        for game in games[-5:]:  # Last 5 meetings
            if game.status == "finished" and game.home_score and game.away_score:
                is_team1_home = team1.lower() in (game.home_team or "").lower()
                if is_team1_home:
                    if game.home_score > game.away_score:
                        h2h["team1_wins"] += 1
                    else:
                        h2h["team2_wins"] += 1
                else:
                    if game.away_score > game.home_score:
                        h2h["team1_wins"] += 1
                    else:
                        h2h["team2_wins"] += 1
                
                h2h["recent_games"].append({
                    "date": game.game_date,
                    "score": f"{game.home_team} {game.home_score} - {game.away_score} {game.away_team}"
                })
        
        return h2h
    
    def get_prop_trends(self, player_name: str, prop_type: str, sport: str, days: int = 30) -> Dict:
        """Get trends for a specific player prop."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        props = self.session.query(PlayerProp).join(Game).filter(
            PlayerProp.player_name.ilike(f"%{player_name}%"),
            (PlayerProp.prop_type == prop_type) | (PlayerProp.market_key == prop_type),
            Game.sport == sport,
            Game.game_date >= cutoff_date
        ).order_by(Game.game_date.desc()).all()
        
        trends = {
            "player_name": player_name,
            "prop_type": prop_type,
            "sport": sport,
            "total_props": len(props),
            "average_line": 0.0,
            "line_trend": "stable",
            "odds_trend": "stable"
        }
        
        if props:
            lines = [p.prop_value for p in props if p.prop_value]
            if lines:
                trends["average_line"] = np.mean(lines)
                # Check if line is trending up or down
                if len(lines) >= 3:
                    recent_avg = np.mean(lines[:3])
                    older_avg = np.mean(lines[-3:])
                    if recent_avg > older_avg * 1.05:
                        trends["line_trend"] = "increasing"
                    elif recent_avg < older_avg * 0.95:
                        trends["line_trend"] = "decreasing"
        
        return trends
    
    def search_players(self, query: str, sport: str) -> List[str]:
        """Search for players by name."""
        props = self.session.query(PlayerProp.player_name).join(Game).filter(
            PlayerProp.player_name.ilike(f"%{query}%"),
            Game.sport == sport
        ).distinct().limit(20).all()
        
        return [p[0] for p in props]
    
    def search_teams(self, query: str, sport: str) -> List[str]:
        """Search for teams by name."""
        teams = set()
        
        # From games
        games = self.session.query(Game).filter(
            Game.sport == sport,
            ((Game.home_team.ilike(f"%{query}%")) | (Game.away_team.ilike(f"%{query}%")))
        ).limit(20).all()
        
        for game in games:
            if game.home_team:
                teams.add(game.home_team)
            if game.away_team:
                teams.add(game.away_team)
        
        return list(teams)[:20]

