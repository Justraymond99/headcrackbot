"""Data intake module for fetching odds, stats, and injury reports."""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from config import (
    SPORTSDATA_API_KEY, ODDS_API_KEY,
    SPORTSDATA_BASE_URL, ODDS_API_BASE_URL
)
from models import Game, PlayerStat, TeamStat, PlayerProp, SessionLocal
from market_definitions import (
    SPORT_PLAYER_PROPS, get_market_description, is_yes_no_prop, is_over_under_prop
)
from all_markets_parser import AllMarketsParser
from comprehensive_markets import get_comprehensive_markets_string
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataIntake:
    """Handle data fetching from various APIs."""
    
    def __init__(self):
        self.sportsdata_key = SPORTSDATA_API_KEY
        self.odds_api_key = ODDS_API_KEY
        self.session = SessionLocal()
        self.all_markets_parser = AllMarketsParser()
    
    def fetch_odds(self, sport: str, markets: str = None) -> List[Dict]:
        """
        Fetch odds from The Odds API with all available markets.
        
        Args:
            sport: Sport key (basketball_nba, americanfootball_nfl, etc.)
            markets: Comma-separated markets (defaults to all available for sport)
        
        Returns:
            List of game odds dictionaries
        """
        if not self.odds_api_key:
            logger.warning("Odds API key not configured. Using mock data.")
            return self._mock_odds_data(sport)
        
        # If no markets specified, use comprehensive markets
        if markets is None:
            # Determine sport abbreviation from API key
            sport_abbr = self._get_sport_abbreviation(sport)
            markets = get_comprehensive_markets_string(sport_abbr, include_player_props=False)
            logger.info(f"Using comprehensive markets for {sport_abbr}: {markets[:100]}...")
        
        url = f"{ODDS_API_BASE_URL}/sports/{sport}/odds"
        params = {
            "apiKey": self.odds_api_key,
            "regions": "us",
            "markets": markets,
            "oddsFormat": "american"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Fetched {len(data)} games for {sport}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching odds: {e}")
            return self._mock_odds_data(sport)
    
    def fetch_player_stats(self, sport: str, date: Optional[str] = None) -> List[Dict]:
        """Fetch player stats and injury reports."""
        if not self.sportsdata_key:
            logger.warning("SportsData API key not configured. Using mock data.")
            return self._mock_player_stats(sport)
        
        # This is a placeholder - adjust endpoint based on actual API
        # SportsData.io has different endpoints for different sports
        date = date or datetime.now().strftime("%Y-%m-%d")
        
        try:
            # Example endpoint structure (adjust based on actual API)
            if sport == "NBA":
                url = f"{SPORTSDATA_BASE_URL}/nba/scores/json/PlayerGameStatsByDate/{date}"
            elif sport == "NFL":
                url = f"{SPORTSDATA_BASE_URL}/nfl/scores/json/PlayerGameStatsByDate/{date}"
            else:
                return self._mock_player_stats(sport)
            
            headers = {"Ocp-Apim-Subscription-Key": self.sportsdata_key}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching player stats: {e}")
            return self._mock_player_stats(sport)
    
    def fetch_team_stats(self, sport: str) -> List[Dict]:
        """Fetch team statistics and streaks."""
        if not self.sportsdata_key:
            return self._mock_team_stats(sport)
        
        try:
            if sport == "NBA":
                url = f"{SPORTSDATA_BASE_URL}/nba/scores/json/Standings/2024"
            elif sport == "NFL":
                url = f"{SPORTSDATA_BASE_URL}/nfl/scores/json/Standings/2024"
            else:
                return self._mock_team_stats(sport)
            
            headers = {"Ocp-Apim-Subscription-Key": self.sportsdata_key}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching team stats: {e}")
            return self._mock_team_stats(sport)
    
    def store_games(self, odds_data: List[Dict], sport: str):
        """Store game data in database."""
        stored_count = 0
        for game_data in odds_data:
            try:
                # Parse odds data (structure varies by API)
                game = self._parse_odds_to_game(game_data, sport)
                
                # For UFC and Boxing, ensure home_team and away_team are set to placeholder values if None
                # (some database schemas may require non-null values)
                if game.sport in ["UFC", "BOXING"] and not game.home_team:
                    prefix = "UFC" if game.sport == "UFC" else "BOXING"
                    game.home_team = f"{prefix}_Fighter1"
                    game.away_team = f"{prefix}_Fighter2"
                
                # Check if game exists
                existing = self.session.query(Game).filter_by(
                    game_id=game.game_id
                ).first()
                
                if existing:
                    # Update existing game
                    for key, value in game.__dict__.items():
                        if not key.startswith('_') and key != 'id' and value is not None:
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                    game = existing  # Use existing for props
                else:
                    self.session.add(game)
                    self.session.flush()  # Get the ID
                
                # Store player props if available (skip for UFC and Boxing)
                if game.sport not in ["UFC", "BOXING"]:
                    self._store_player_props(game_data, game)
                
                stored_count += 1
                
            except Exception as e:
                logger.error(f"Error storing game: {e}")
                self.session.rollback()  # Rollback on error to allow next game to be processed
                continue
        
        try:
            self.session.commit()
            logger.info(f"Stored {stored_count} games for {sport}")
        except Exception as e:
            logger.error(f"Error committing games: {e}")
            self.session.rollback()
    
    def fetch_event_odds(self, event_id: str, sport: str = None, markets: str = None) -> Dict:
        """
        Fetch odds for a specific event including ALL available markets and player props.
        
        Args:
            event_id: Event ID from API
            sport: Sport abbreviation (NBA, NFL, etc.) - helps determine which props to fetch
            markets: Specific markets to fetch (defaults to all available)
        """
        if not self.odds_api_key:
            return {}
        
        # Get all available markets if not specified
        if markets is None:
            # Start with main markets
            if sport:
                markets = get_comprehensive_markets_string(sport, include_player_props=False)
            else:
                markets = "h2h,spreads,totals,alternate_spreads,alternate_totals,team_totals,alternate_team_totals"
            
            # Add all player props if sport specified and not combat sport
            if sport and sport not in ["UFC", "BOXING"]:
                from comprehensive_markets import get_all_player_props_for_sport
                player_props = get_all_player_props_for_sport(sport)
                if player_props:
                    # Add player props (limit to most common to avoid API limits)
                    common_props = player_props[:30]  # Top 30 props
                    markets += "," + ",".join(common_props)
        
        url = f"{ODDS_API_BASE_URL}/events/{event_id}/odds"
        params = {
            "apiKey": self.odds_api_key,
            "regions": "us",
            "markets": markets,
            "oddsFormat": "american"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching event odds: {e}")
            return {}
    
    def _store_player_props(self, odds_data: Dict, game: Game):
        """Extract and store player props from odds data."""
        bookmakers = odds_data.get("bookmakers", [])
        if not bookmakers:
            return
        
        # Determine sport for prop market keys
        sport = game.sport.upper()
        available_props = SPORT_PLAYER_PROPS.get(sport, [])
        
        props_stored = 0
        
        for book in bookmakers:
            markets = book.get("markets", [])
            for market in markets:
                market_key = market.get("key", "")
                
                # Check if this is a player prop market
                if market_key in available_props or market_key.startswith("player_") or market_key.startswith("batter_") or market_key.startswith("pitcher_"):
                    outcomes = market.get("outcomes", [])
                    
                    for outcome in outcomes:
                        player_name = outcome.get("name", "")
                        description = outcome.get("description", "").lower() if outcome.get("description") else ""
                        point = outcome.get("point")  # For Over/Under props
                        price = outcome.get("price")
                        
                        # Parse player name from outcome name if needed
                        # Format might be "Player Name - Prop Type - Over/Under Value"
                        if " - " in player_name:
                            parts = player_name.split(" - ")
                            if len(parts) >= 3:
                                player_name = parts[0].strip()
                                # Extract prop value from last part if not in point field
                                if point is None:
                                    try:
                                        point = float(parts[-1].strip())
                                    except:
                                        pass
                        
                        # Handle Yes/No props
                        if is_yes_no_prop(market_key):
                            # Yes/No props (e.g., anytime TD scorer)
                            existing = self.session.query(PlayerProp).filter_by(
                                game_id=game.id,
                                player_name=player_name,
                                market_key=market_key
                            ).first()
                            
                            if not existing:
                                prop = PlayerProp(
                                    game_id=game.id,
                                    player_name=player_name,
                                    prop_type=market_key,
                                    market_key=market_key,
                                    description=get_market_description(market_key),
                                    prop_value=None,
                                    yes_odds=price if "yes" in description else None,
                                    no_odds=price if "no" in description else None
                                )
                                self.session.add(prop)
                                props_stored += 1
                            else:
                                if "yes" in description:
                                    existing.yes_odds = price
                                elif "no" in description:
                                    existing.no_odds = price
                        
                        # Handle Over/Under props
                        elif is_over_under_prop(market_key) and point is not None:
                            # Determine over/under from description or outcome name
                            is_over = "over" in description or "over" in player_name.lower()
                            is_under = "under" in description or "under" in player_name.lower()
                            
                            existing = self.session.query(PlayerProp).filter_by(
                                game_id=game.id,
                                player_name=player_name.split(" - ")[0] if " - " in player_name else player_name,
                                market_key=market_key,
                                prop_value=point
                            ).first()
                            
                            if not existing:
                                # Extract clean player name
                                clean_player_name = player_name.split(" - ")[0] if " - " in player_name else player_name
                                
                                prop = PlayerProp(
                                    game_id=game.id,
                                    player_name=clean_player_name,
                                    prop_type=market_key,
                                    market_key=market_key,
                                    description=get_market_description(market_key),
                                    prop_value=point,
                                    over_odds=price if is_over else None,
                                    under_odds=price if is_under else None
                                )
                                self.session.add(prop)
                                props_stored += 1
                            else:
                                if is_over:
                                    existing.over_odds = price
                                elif is_under:
                                    existing.under_odds = price
        
        if props_stored > 0:
            logger.info(f"Stored {props_stored} player props for game {game.id}")
    
    def _parse_odds_to_game(self, odds_data: Dict, sport: str) -> Game:
        """Parse odds API response to Game model."""
        # Handle UFC/Boxing vs team sports
        is_ufc = "mma" in sport.lower() or sport.upper() == "UFC"
        is_boxing = "boxing" in sport.lower() or sport.upper() == "BOXING"
        is_combat_sport = is_ufc or is_boxing
        
        if is_combat_sport:
            # UFC/Boxing format - fighters instead of teams
            fighters = odds_data.get("sport_title", "").split(" vs ") if "vs" in odds_data.get("sport_title", "") else []
            fighter1 = odds_data.get("home_team") or (fighters[0] if len(fighters) > 0 else "Fighter 1")
            fighter2 = odds_data.get("away_team") or (fighters[1] if len(fighters) > 1 else "Fighter 2")
            home_team = away_team = None
        else:
            home_team = odds_data.get("home_team", "Unknown")
            away_team = odds_data.get("away_team", "Unknown")
            fighter1 = fighter2 = None
        
        # Parse date - handle ISO format with 'Z' suffix
        commence_time = odds_data.get("commence_time", datetime.now().isoformat())
        if commence_time.endswith('Z'):
            commence_time = commence_time[:-1] + '+00:00'
        try:
            game_date = datetime.fromisoformat(commence_time)
        except ValueError:
            # Fallback to current time if parsing fails
            game_date = datetime.now()
        
        # Extract odds from bookmakers
        # Initialize all variables first
        home_ml = away_ml = fighter1_ml = fighter2_ml = None
        spread = spread_home = spread_away = None
        total = over_odds = under_odds = None
        
        bookmakers = odds_data.get("bookmakers", [])
        if bookmakers:
            book = bookmakers[0]  # Use first bookmaker
            markets = book.get("markets", [])
            
            for market in markets:
                if market["key"] == "h2h":  # Moneyline
                    outcomes = market.get("outcomes", [])
                    for outcome in outcomes:
                        name = outcome.get("name", "")
                        if is_combat_sport:
                            if name == fighter1 or (fighter1 and name in fighter1):
                                fighter1_ml = outcome.get("price")
                            elif name == fighter2 or (fighter2 and name in fighter2):
                                fighter2_ml = outcome.get("price")
                        else:
                            if name == home_team:
                                home_ml = outcome.get("price")
                            elif name == away_team:
                                away_ml = outcome.get("price")
                
                elif market["key"] == "spreads" and not is_combat_sport:
                    outcomes = market.get("outcomes", [])
                    for outcome in outcomes:
                        if outcome["name"] == home_team:
                            spread = outcome.get("point")
                            spread_home = outcome.get("price")
                        elif outcome["name"] == away_team:
                            spread_away = outcome.get("price")
                
                elif market["key"] == "totals" and not is_combat_sport:
                    outcomes = market.get("outcomes", [])
                    for outcome in outcomes:
                        if outcome["name"] == "Over":
                            total = outcome.get("point")
                            over_odds = outcome.get("price")
                        elif outcome["name"] == "Under":
                            under_odds = outcome.get("price")
        
        # Create game ID
        if is_combat_sport:
            sport_prefix = "UFC" if is_ufc else "BOXING"
            game_id = f"{sport_prefix}_{fighter1}_{fighter2}_{game_date.strftime('%Y%m%d')}"
        else:
            game_id = f"{sport}_{home_team}_{away_team}_{game_date.strftime('%Y%m%d')}"
        
        return Game(
            game_id=game_id,
            sport="UFC" if is_ufc else ("BOXING" if is_boxing else sport.upper()),
            home_team=home_team,
            away_team=away_team,
            fighter1=fighter1,
            fighter2=fighter2,
            game_date=game_date,
            status="scheduled",
            home_moneyline=home_ml or fighter1_ml,
            away_moneyline=away_ml or fighter2_ml,
            spread=spread,
            spread_home_odds=spread_home,
            spread_away_odds=spread_away,
            total=total,
            over_odds=over_odds,
            under_odds=under_odds
        )
    
    def _mock_odds_data(self, sport: str) -> List[Dict]:
        """Generate mock odds data for testing."""
        teams = {
            "basketball_nba": [
                ("Lakers", "Warriors"), ("Celtics", "Heat"),
                ("Nets", "Bucks"), ("Suns", "Mavericks")
            ],
            "americanfootball_nfl": [
                ("Chiefs", "Bills"), ("49ers", "Cowboys"),
                ("Eagles", "Packers"), ("Ravens", "Bengals")
            ],
            "mma_mixed_martial_arts": [
                ("Jon Jones", "Stipe Miocic"), ("Islam Makhachev", "Charles Oliveira"),
                ("Alex Pereira", "Jiri Prochazka"), ("Leon Edwards", "Colby Covington")
            ]
        }
        
        sport_teams = teams.get(sport, [("Team A", "Team B"), ("Team C", "Team D")])
        mock_games = []
        is_ufc = "mma" in sport.lower()
        is_boxing = "boxing" in sport.lower()
        is_combat_sport = is_ufc or is_boxing
        
        for home, away in sport_teams:
            markets = [
                {
                    "key": "h2h",
                    "outcomes": [
                        {"name": home, "price": -110},
                        {"name": away, "price": -110}
                    ]
                }
            ]
            
            # Add spreads and totals only for team sports (not combat sports)
            if not is_combat_sport:
                markets.extend([
                    {
                        "key": "spreads",
                        "outcomes": [
                            {"name": home, "point": -3.5, "price": -110},
                            {"name": away, "point": 3.5, "price": -110}
                        ]
                    },
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "point": 220.5, "price": -110},
                            {"name": "Under", "point": 220.5, "price": -110}
                        ]
                    }
                ])
            
            # Add player props for NBA (more comprehensive)
            if sport == "basketball_nba":
                player_props = []
                # Add props for multiple players
                for team_name in [home, away]:
                    player_props.extend([
                        {
                            "name": f"{team_name} Player A - Points - Over 25.5",
                            "description": "Over",
                            "point": 25.5,
                            "price": -110
                        },
                        {
                            "name": f"{team_name} Player A - Points - Under 25.5",
                            "description": "Under",
                            "point": 25.5,
                            "price": -110
                        },
                        {
                            "name": f"{team_name} Player B - Rebounds - Over 8.5",
                            "description": "Over",
                            "point": 8.5,
                            "price": -110
                        },
                        {
                            "name": f"{team_name} Player B - Rebounds - Under 8.5",
                            "description": "Under",
                            "point": 8.5,
                            "price": -110
                        },
                        {
                            "name": f"{team_name} Player C - Assists - Over 6.5",
                            "description": "Over",
                            "point": 6.5,
                            "price": -110
                        },
                        {
                            "name": f"{team_name} Player C - Assists - Under 6.5",
                            "description": "Under",
                            "point": 6.5,
                            "price": -110
                        }
                    ])
                
                markets.append({
                    "key": "player_points",
                    "outcomes": [p for p in player_props if "Points" in p["name"]]
                })
                markets.append({
                    "key": "player_rebounds",
                    "outcomes": [p for p in player_props if "Rebounds" in p["name"]]
                })
                markets.append({
                    "key": "player_assists",
                    "outcomes": [p for p in player_props if "Assists" in p["name"]]
                })
            
            mock_games.append({
                "home_team": home,
                "away_team": away,
                "commence_time": (datetime.now() + timedelta(days=1)).isoformat(),
                "bookmakers": [{
                    "key": "draftkings",
                    "markets": markets
                }]
            })
        
        return mock_games
    
    def _mock_player_stats(self, sport: str) -> List[Dict]:
        """Generate mock player stats."""
        return [
            {
                "player_name": "Player A",
                "team": "Lakers",
                "injury_status": "healthy",
                "points": 25.5,
                "rebounds": 8.2
            }
        ]
    
    def _mock_team_stats(self, sport: str) -> List[Dict]:
        """Generate mock team stats."""
        return [
            {
                "team": "Lakers",
                "win_streak": 3,
                "home_record": "15-5",
                "offensive_rating": 115.2
            }
        ]
    
    def fetch_all_data(self, sports: List[str], fetch_player_props: bool = True):
        """Fetch and store all data for given sports."""
        sport_mapping = {
            "NBA": "basketball_nba",
            "NFL": "americanfootball_nfl",
            "MLB": "baseball_mlb",
            "NHL": "icehockey_nhl",
            "UFC": "mma_mixed_martial_arts",
            "BOXING": "boxing_boxing"
        }
        
        for sport in sports:
            odds_sport = sport_mapping.get(sport, sport.lower())
            logger.info(f"Fetching data for {sport}...")
            
            # Fetch main odds (h2h, spreads, totals)
            odds_data = self.fetch_odds(odds_sport)
            self.store_games(odds_data, sport)
            
            # Fetch comprehensive odds and player props for each event if enabled
            if fetch_player_props and sport not in ["UFC", "BOXING"]:
                logger.info(f"Fetching comprehensive odds and player props for {sport}...")
                for game_data in odds_data:
                    event_id = game_data.get("id")
                    if event_id:
                        # Fetch ALL markets including player props
                        event_odds = self.fetch_event_odds(event_id, sport=sport)
                        if event_odds:
                            # Find the game in database
                            game = self.session.query(Game).filter_by(
                                game_id=self._get_game_id_from_event(game_data, sport)
                            ).first()
                            if game:
                                # Store ALL markets (alternate spreads, totals, team totals, periods, etc.)
                                self.all_markets_parser.store_all_markets_as_props(event_odds, game)
                                # Store player props
                                self._store_player_props(event_odds, game)
                                self.session.commit()
            
            # Fetch team stats
            team_stats = self.fetch_team_stats(sport)
            # Store team stats (implementation similar to store_games)
            
        logger.info("Data intake complete!")
    
    def _get_sport_abbreviation(self, api_sport_key: str) -> str:
        """Convert API sport key to abbreviation."""
        mapping = {
            "basketball_nba": "NBA",
            "americanfootball_nfl": "NFL",
            "baseball_mlb": "MLB",
            "icehockey_nhl": "NHL",
            "mma_mixed_martial_arts": "UFC",
            "boxing_boxing": "BOXING"
        }
        return mapping.get(api_sport_key.lower(), api_sport_key.upper())
    
    def _get_game_id_from_event(self, event_data: Dict, sport: str) -> str:
        """Generate game_id from event data."""
        home = event_data.get("home_team", "")
        away = event_data.get("away_team", "")
        commence_time = event_data.get("commence_time", datetime.now().isoformat())
        
        if "mma" in sport.lower() or sport.upper() == "UFC":
            return f"UFC_{home}_{away}_{commence_time[:10].replace('-', '')}"
        elif "boxing" in sport.lower() or sport.upper() == "BOXING":
            return f"BOXING_{home}_{away}_{commence_time[:10].replace('-', '')}"
        return f"{sport}_{home}_{away}_{commence_time[:10].replace('-', '')}"
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

