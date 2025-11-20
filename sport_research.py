"""Sport-specific research features - different analysis for each sport."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Game, PlayerProp, SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SportResearch:
    """Sport-specific research features."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def analyze_nba_game(self, game: Game) -> Dict:
        """NBA-specific analysis."""
        analysis = {
            "pace_analysis": {},
            "player_matchups": {},
            "rest_advantage": None,
            "key_insights": []
        }
        
        # Get player props for this game
        props = self.session.query(PlayerProp).filter_by(game_id=game.id).all()
        
        # Analyze top players
        top_players = {}
        for prop in props:
            player = prop.player_name
            if player not in top_players:
                top_players[player] = {
                    "props": [],
                    "avg_line": 0.0
                }
            top_players[player]["props"].append(prop)
            if prop.prop_value:
                top_players[player]["avg_line"] = (
                    top_players[player]["avg_line"] * (len(top_players[player]["props"]) - 1) + prop.prop_value
                ) / len(top_players[player]["props"])
        
        analysis["top_players"] = dict(sorted(
            top_players.items(),
            key=lambda x: len(x[1]["props"]),
            reverse=True
        )[:10])
        
        # Generate insights
        if len(props) > 20:
            analysis["key_insights"].append(f"High prop availability: {len(props)} props available")
        
        return analysis
    
    def analyze_nfl_game(self, game: Game) -> Dict:
        """NFL-specific analysis."""
        analysis = {
            "weather_impact": None,
            "injury_report": {},
            "key_matchups": {},
            "key_insights": []
        }
        
        # Get player props
        props = self.session.query(PlayerProp).filter_by(game_id=game.id).all()
        
        # Analyze by position
        positions = {
            "QB": [],
            "RB": [],
            "WR": [],
            "TE": [],
            "DEF": []
        }
        
        for prop in props:
            # Try to infer position from prop type
            if "pass" in prop.market_key.lower() or "pass" in (prop.prop_type or "").lower():
                positions["QB"].append(prop)
            elif "rush" in prop.market_key.lower() or "rush" in (prop.prop_type or "").lower():
                positions["RB"].append(prop)
            elif "reception" in prop.market_key.lower() or "reception" in (prop.prop_type or "").lower():
                if len(positions["WR"]) < len(positions["TE"]):
                    positions["WR"].append(prop)
                else:
                    positions["TE"].append(prop)
        
        analysis["positions"] = {k: len(v) for k, v in positions.items() if v}
        
        return analysis
    
    def analyze_mlb_game(self, game: Game) -> Dict:
        """MLB-specific analysis."""
        analysis = {
            "pitcher_matchup": {},
            "ballpark_factors": {},
            "lineup_analysis": {},
            "key_insights": []
        }
        
        props = self.session.query(PlayerProp).filter_by(game_id=game.id).all()
        
        # Separate batter and pitcher props
        batters = [p for p in props if p.market_key and "batter" in p.market_key.lower()]
        pitchers = [p for p in props if p.market_key and "pitcher" in p.market_key.lower()]
        
        analysis["batter_count"] = len(set(p.player_name for p in batters))
        analysis["pitcher_count"] = len(set(p.player_name for p in pitchers))
        
        if pitchers:
            analysis["key_insights"].append(f"Pitcher props available: {len(pitchers)}")
        if batters:
            analysis["key_insights"].append(f"Batter props available: {len(batters)}")
        
        return analysis
    
    def analyze_nhl_game(self, game: Game) -> Dict:
        """NHL-specific analysis."""
        analysis = {
            "goalie_matchup": {},
            "power_play_analysis": {},
            "key_insights": []
        }
        
        props = self.session.query(PlayerProp).filter_by(game_id=game.id).all()
        
        # Find goalie props
        goalies = [p for p in props if "save" in (p.market_key or "").lower() or "save" in (p.prop_type or "").lower()]
        skaters = [p for p in props if p not in goalies]
        
        analysis["goalie_props"] = len(goalies)
        analysis["skater_props"] = len(skaters)
        
        return analysis
    
    def analyze_ufc_fight(self, game: Game) -> Dict:
        """UFC-specific analysis."""
        analysis = {
            "fighter_comparison": {},
            "finish_probability": {},
            "key_insights": []
        }
        
        # UFC fights have fighter1 and fighter2
        if game.fighter1 and game.fighter2:
            analysis["fighters"] = {
                "fighter1": game.fighter1,
                "fighter2": game.fighter2
            }
            
            # Analyze odds
            if game.home_moneyline and game.away_moneyline:
                analysis["odds_favorite"] = game.fighter1 if abs(game.home_moneyline) < abs(game.away_moneyline) else game.fighter2
                analysis["key_insights"].append(f"Favorite: {analysis['odds_favorite']}")
        
        return analysis
    
    def analyze_game(self, game: Game) -> Dict:
        """Analyze game with sport-specific features."""
        sport = game.sport.upper()
        
        if sport == "NBA":
            return self.analyze_nba_game(game)
        elif sport == "NFL":
            return self.analyze_nfl_game(game)
        elif sport == "MLB":
            return self.analyze_mlb_game(game)
        elif sport == "NHL":
            return self.analyze_nhl_game(game)
        elif sport == "UFC":
            return self.analyze_ufc_fight(game)
        else:
            return {"message": f"Analysis for {sport} coming soon"}

