"""DICEgpt - AI-powered sports betting assistant with natural language interface."""
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from models import Game, Leg, Parlay, PlayerProp, SessionLocal
from research_engine import ResearchEngine
from ai_picks import AIPicks
from stat_shack import StatShack
from sport_research import SportResearch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DICEgpt:
    """AI assistant for sports betting with natural language queries."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.research_engine = ResearchEngine()
        self.ai_picks = AIPicks()
        self.stat_shack = StatShack()
        self.sport_research = SportResearch()
    
    def parse_query(self, query: str) -> Dict:
        """Parse natural language query to extract intent and parameters."""
        query_lower = query.lower()
        
        parsed = {
            "intent": "general",
            "sport": None,
            "bet_type": None,
            "num_picks": 5,
            "filters": {},
            "tagged_entities": [],
            "constraints": {}
        }
        
        # Extract @ mentions
        mentions = re.findall(r'@(\w+(?:\s+\w+)*)', query)
        parsed["tagged_entities"] = mentions
        
        # Detect intent
        if any(word in query_lower for word in ["pick", "best", "top", "give me", "show me"]):
            parsed["intent"] = "get_picks"
        elif any(word in query_lower for word in ["parlay", "build", "create", "construct"]):
            parsed["intent"] = "build_parlay"
        elif any(word in query_lower for word in ["research", "analyze", "how", "what", "why"]):
            parsed["intent"] = "research"
        elif any(word in query_lower for word in ["matchup", "h2h", "head to head"]):
            parsed["intent"] = "matchup"
        
        # Extract sport
        sports = ["nba", "nfl", "mlb", "nhl", "ufc", "soccer", "ncaab", "ncaaf"]
        for sport in sports:
            if sport in query_lower:
                parsed["sport"] = sport.upper()
                break
        
        # Extract number of picks
        num_match = re.search(r'(\d+)\s*(?:pick|leg|bet)', query_lower)
        if num_match:
            parsed["num_picks"] = int(num_match.group(1))
        
        # Extract bet types
        if "prop" in query_lower or "player prop" in query_lower:
            parsed["bet_type"] = "prop"
        elif "moneyline" in query_lower or "ml" in query_lower:
            parsed["bet_type"] = "moneyline"
        elif "spread" in query_lower:
            parsed["bet_type"] = "spread"
        elif "total" in query_lower or "over/under" in query_lower:
            parsed["bet_type"] = "total"
        elif "parlay" in query_lower:
            parsed["bet_type"] = "parlay"
        
        # Extract constraints
        if "safe" in query_lower or "conservative" in query_lower:
            parsed["constraints"]["risk"] = "low"
        elif "long shot" in query_lower or "upset" in query_lower:
            parsed["constraints"]["risk"] = "high"
        
        if "+" in query or "plus odds" in query_lower:
            parsed["constraints"]["min_odds"] = 0  # Positive odds
        elif re.search(r'odds?\s*(?:no\s*worse\s*than|better\s*than|>|>=)\s*([+-]?\d+)', query_lower):
            odds_match = re.search(r'([+-]?\d+)', query)
            if odds_match:
                parsed["constraints"]["min_odds"] = int(odds_match.group(1))
        
        # Extract specific prop types
        prop_types = ["points", "rebounds", "assists", "home runs", "strikeouts", "tds", "goals"]
        for prop_type in prop_types:
            if prop_type in query_lower:
                parsed["filters"]["prop_type"] = prop_type
                break
        
        return parsed
    
    def get_picks(self, query: str) -> List[Dict]:
        """Get picks based on natural language query."""
        parsed = self.parse_query(query)
        
        # Get games
        games = self.session.query(Game).filter(
            Game.status == "scheduled"
        ).all()
        
        if parsed["sport"]:
            games = [g for g in games if g.sport == parsed["sport"]]
        
        if not games:
            return []
        
        # Get AI picks
        picks = self.ai_picks.generate_ai_picks(games, max_picks=parsed["num_picks"] * 2)
        
        # Apply filters
        if parsed["bet_type"]:
            picks = [p for p in picks if p["leg"]["bet_type"] == parsed["bet_type"]]
        
        if parsed["filters"].get("prop_type"):
            prop_type = parsed["filters"]["prop_type"]
            picks = [p for p in picks if prop_type in (p["leg"].get("prop_type") or "").lower()]
        
        if parsed["constraints"].get("min_odds") is not None:
            min_odds = parsed["constraints"]["min_odds"]
            if min_odds >= 0:
                picks = [p for p in picks if p["odds"] >= min_odds]
            else:
                picks = [p for p in picks if p["odds"] <= min_odds]
        
        # Apply risk constraints
        if parsed["constraints"].get("risk") == "low":
            picks = sorted(picks, key=lambda x: x["confidence"], reverse=True)[:parsed["num_picks"]]
        elif parsed["constraints"].get("risk") == "high":
            picks = sorted(picks, key=lambda x: x["odds"], reverse=True)[:parsed["num_picks"]]
        else:
            picks = sorted(picks, key=lambda x: x["ai_score"], reverse=True)[:parsed["num_picks"]]
        
        return picks[:parsed["num_picks"]]
    
    def build_parlay(self, query: str) -> Dict:
        """Build a parlay based on natural language query."""
        parsed = self.parse_query(query)
        
        games = self.session.query(Game).filter(
            Game.status == "scheduled"
        ).all()
        
        if parsed["sport"]:
            games = [g for g in games if g.sport == parsed["sport"]]
        
        # Generate parlay
        if "same game" in query.lower() or "sgp" in query.lower():
            # Same game parlay
            if games:
                game = games[0]  # Use first game
                parlays = self.research_engine.generate_same_game_parlays(game, max_parlays=1)
                if parlays:
                    return parlays[0]
        else:
            # Regular parlay
            parlays = self.research_engine.generate_parlays(games, max_parlays=1, include_sgp=False)
            if parlays:
                return parlays[0]
        
        return None
    
    def research(self, query: str) -> Dict:
        """Research and analyze based on query."""
        parsed = self.parse_query(query)
        response = {
            "answer": "",
            "data": {},
            "insights": []
        }
        
        # Handle @ mentions
        if parsed["tagged_entities"]:
            entity = parsed["tagged_entities"][0]
            
            # Try to find player
            players = self.stat_shack.search_players(entity, parsed["sport"] or "NBA")
            if players:
                player = players[0]
                stats = self.stat_shack.get_player_stats(player, parsed["sport"] or "NBA")
                response["data"] = stats
                response["answer"] = f"Here's what I found about {player}:"
                response["insights"].append(f"Analyzed {stats['games_analyzed']} games")
            
            # Try to find team
            teams = self.stat_shack.search_teams(entity, parsed["sport"] or "NBA")
            if teams:
                team = teams[0]
                stats = self.stat_shack.get_team_stats(team, parsed["sport"] or "NBA")
                response["data"] = stats
                response["answer"] = f"Here's what I found about {team}:"
        
        # Handle matchup queries
        if "vs" in query.lower() or "versus" in query.lower():
            teams = re.findall(r'@?(\w+(?:\s+\w+)*)', query)
            if len(teams) >= 2:
                team1, team2 = teams[0], teams[1]
                h2h = self.stat_shack.get_head_to_head(team1, team2, parsed["sport"] or "NBA")
                response["data"] = h2h
                response["answer"] = f"Head-to-head: {team1} vs {team2}"
        
        return response
    
    def process_query(self, query: str) -> Dict:
        """Process a natural language query and return response."""
        parsed = self.parse_query(query)
        
        response = {
            "query": query,
            "intent": parsed["intent"],
            "results": [],
            "message": "",
            "success": True
        }
        
        try:
            if parsed["intent"] == "get_picks":
                picks = self.get_picks(query)
                response["results"] = picks
                response["message"] = f"Found {len(picks)} picks based on your query"
            
            elif parsed["intent"] == "build_parlay":
                parlay = self.build_parlay(query)
                if parlay:
                    response["results"] = [parlay]
                    response["message"] = "Built a parlay based on your criteria"
                else:
                    response["message"] = "Couldn't build a parlay matching your criteria"
                    response["success"] = False
            
            elif parsed["intent"] in ["research", "matchup"]:
                research_result = self.research(query)
                response["results"] = [research_result]
                response["message"] = research_result.get("answer", "Research completed")
            
            else:
                # General query - try to get picks
                picks = self.get_picks(query)
                response["results"] = picks
                response["message"] = f"Here are {len(picks)} picks for today"
        
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            response["success"] = False
            response["message"] = f"Error: {str(e)}"
        
        return response

