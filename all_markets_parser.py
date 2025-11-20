"""Parser for all betting markets including alternate lines, team totals, and period markets."""
from typing import List, Dict, Optional
from models import Game, PlayerProp, SessionLocal
from market_definitions import get_market_description, is_yes_no_prop, is_over_under_prop
import logging

logger = logging.getLogger(__name__)


class AllMarketsParser:
    """Parse and store all betting markets from API responses."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def parse_all_markets_from_event(
        self,
        event_data: Dict,
        game: Game
    ) -> List[Dict]:
        """
        Parse ALL markets from an event API response.
        
        This includes:
        - Basic markets (h2h, spreads, totals)
        - Alternate markets (alternate_spreads, alternate_totals)
        - Team totals
        - Period markets (quarters, halves, periods, innings)
        - Player props
        
        Args:
            event_data: Full event data from API
            game: Game database object
        
        Returns:
            List of all available betting options as leg dictionaries
        """
        all_legs = []
        bookmakers = event_data.get("bookmakers", [])
        
        if not bookmakers:
            return all_legs
        
        # Use first bookmaker or aggregate across all
        for bookmaker in bookmakers:
            markets = bookmaker.get("markets", [])
            
            for market in markets:
                market_key = market.get("key", "")
                outcomes = market.get("outcomes", [])
                
                # Parse based on market type
                if market_key == "h2h":
                    all_legs.extend(self._parse_h2h_market(outcomes, game, market_key))
                
                elif market_key == "spreads":
                    all_legs.extend(self._parse_spread_market(outcomes, game, market_key))
                
                elif market_key == "totals":
                    all_legs.extend(self._parse_total_market(outcomes, game, market_key))
                
                elif "alternate_spreads" in market_key:
                    all_legs.extend(self._parse_spread_market(outcomes, game, market_key, is_alternate=True))
                
                elif "alternate_totals" in market_key:
                    all_legs.extend(self._parse_total_market(outcomes, game, market_key, is_alternate=True))
                
                elif "team_totals" in market_key:
                    all_legs.extend(self._parse_team_total_market(outcomes, game, market_key))
                
                elif "_q1" in market_key or "_q2" in market_key or "_q3" in market_key or "_q4" in market_key:
                    # Quarter markets
                    all_legs.extend(self._parse_period_market(outcomes, game, market_key, period_type="quarter"))
                
                elif "_h1" in market_key or "_h2" in market_key:
                    # Half markets
                    all_legs.extend(self._parse_period_market(outcomes, game, market_key, period_type="half"))
                
                elif "_p1" in market_key or "_p2" in market_key or "_p3" in market_key:
                    # Period markets (hockey)
                    all_legs.extend(self._parse_period_market(outcomes, game, market_key, period_type="period"))
                
                elif "innings" in market_key:
                    # Innings markets (baseball)
                    all_legs.extend(self._parse_period_market(outcomes, game, market_key, period_type="innings"))
                
                elif market_key.startswith("player_") or market_key.startswith("batter_") or market_key.startswith("pitcher_"):
                    # Player props - already handled by _store_player_props
                    continue
        
        return all_legs
    
    def _parse_h2h_market(
        self,
        outcomes: List[Dict],
        game: Game,
        market_key: str
    ) -> List[Dict]:
        """Parse head-to-head (moneyline) market."""
        legs = []
        
        for outcome in outcomes:
            name = outcome.get("name", "")
            odds = outcome.get("price")
            
            if not odds:
                continue
            
            # Determine selection
            if game.sport in ["UFC", "BOXING"]:
                if name == game.fighter1 or (game.fighter1 and name in game.fighter1):
                    selection = game.fighter1
                    bet_type = "fighter_moneyline" if game.sport == "UFC" else "boxing_moneyline"
                elif name == game.fighter2 or (game.fighter2 and name in game.fighter2):
                    selection = game.fighter2
                    bet_type = "fighter_moneyline" if game.sport == "UFC" else "boxing_moneyline"
                else:
                    continue
            else:
                if name == game.home_team:
                    selection = game.home_team
                elif name == game.away_team:
                    selection = game.away_team
                else:
                    continue
                bet_type = "moneyline"
            
            legs.append({
                "game": game,
                "bet_type": bet_type,
                "selection": selection,
                "odds": odds,
                "market_key": market_key,
                "description": get_market_description(market_key)
            })
        
        return legs
    
    def _parse_spread_market(
        self,
        outcomes: List[Dict],
        game: Game,
        market_key: str,
        is_alternate: bool = False
    ) -> List[Dict]:
        """Parse spread market."""
        legs = []
        
        if game.sport in ["UFC", "BOXING"]:
            return legs  # No spreads for combat sports
        
        for outcome in outcomes:
            name = outcome.get("name", "")
            point = outcome.get("point")
            odds = outcome.get("price")
            
            if not odds or point is None:
                continue
            
            if name == game.home_team:
                selection = f"{game.home_team} {point:+.1f}"
            elif name == game.away_team:
                selection = f"{game.away_team} {abs(point):+.1f}"
            else:
                continue
            
            bet_type = "alternate_spread" if is_alternate else "spread"
            
            legs.append({
                "game": game,
                "bet_type": bet_type,
                "selection": selection,
                "odds": odds,
                "spread_value": point,
                "market_key": market_key,
                "description": f"{get_market_description(market_key)} {point:+.1f}"
            })
        
        return legs
    
    def _parse_total_market(
        self,
        outcomes: List[Dict],
        game: Game,
        market_key: str,
        is_alternate: bool = False
    ) -> List[Dict]:
        """Parse total (over/under) market."""
        legs = []
        
        if game.sport in ["UFC", "BOXING"]:
            return legs  # No totals for combat sports
        
        total_line = None
        over_odds = None
        under_odds = None
        
        for outcome in outcomes:
            name = outcome.get("name", "")
            point = outcome.get("point")
            odds = outcome.get("price")
            
            if point is not None:
                total_line = point
            
            if name == "Over":
                over_odds = odds
            elif name == "Under":
                under_odds = odds
        
        if total_line:
            bet_type = "alternate_total" if is_alternate else "total"
            
            if over_odds:
                legs.append({
                    "game": game,
                    "bet_type": bet_type,
                    "selection": f"Over {total_line:.1f}",
                    "odds": over_odds,
                    "total_value": total_line,
                    "market_key": market_key,
                    "description": f"Over {total_line:.1f}"
                })
            
            if under_odds:
                legs.append({
                    "game": game,
                    "bet_type": bet_type,
                    "selection": f"Under {total_line:.1f}",
                    "odds": under_odds,
                    "total_value": total_line,
                    "market_key": market_key,
                    "description": f"Under {total_line:.1f}"
                })
        
        return legs
    
    def _parse_team_total_market(
        self,
        outcomes: List[Dict],
        game: Game,
        market_key: str
    ) -> List[Dict]:
        """Parse team total market."""
        legs = []
        
        if game.sport in ["UFC", "BOXING"]:
            return legs
        
        # Team totals: "Team Name Over X" or "Team Name Under X"
        for outcome in outcomes:
            name = outcome.get("name", "")
            point = outcome.get("point")
            odds = outcome.get("price")
            
            if not odds or point is None:
                continue
            
            # Parse team name and over/under from name
            if "Over" in name:
                team_name = name.replace("Over", "").strip()
                selection = f"{team_name} Over {point:.1f}"
            elif "Under" in name:
                team_name = name.replace("Under", "").strip()
                selection = f"{team_name} Under {point:.1f}"
            else:
                # Try to match by team name
                if game.home_team in name:
                    team_name = game.home_team
                    if "Over" in name or point > game.total / 2:
                        selection = f"{team_name} Over {point:.1f}"
                    else:
                        selection = f"{team_name} Under {point:.1f}"
                elif game.away_team in name:
                    team_name = game.away_team
                    if "Over" in name or point > game.total / 2:
                        selection = f"{team_name} Over {point:.1f}"
                    else:
                        selection = f"{team_name} Under {point:.1f}"
                else:
                    continue
            
            legs.append({
                "game": game,
                "bet_type": "team_total",
                "selection": selection,
                "odds": odds,
                "team_total_value": point,
                "market_key": market_key,
                "description": f"Team Total: {selection}"
            })
        
        return legs
    
    def _parse_period_market(
        self,
        outcomes: List[Dict],
        game: Game,
        market_key: str,
        period_type: str = "quarter"
    ) -> List[Dict]:
        """Parse period-specific markets (quarters, halves, periods, innings)."""
        legs = []
        
        if game.sport in ["UFC", "BOXING"]:
            return legs  # No period markets for combat sports (except rounds, but those are different)
        
        # Extract period number from market key
        period_num = None
        if "_q1" in market_key:
            period_num = 1
        elif "_q2" in market_key:
            period_num = 2
        elif "_q3" in market_key:
            period_num = 3
        elif "_q4" in market_key:
            period_num = 4
        elif "_h1" in market_key:
            period_num = 1
        elif "_h2" in market_key:
            period_num = 2
        elif "_p1" in market_key:
            period_num = 1
        elif "_p2" in market_key:
            period_num = 2
        elif "_p3" in market_key:
            period_num = 3
        elif "1st_1_innings" in market_key:
            period_num = 1
        elif "1st_3_innings" in market_key:
            period_num = 3
        elif "1st_5_innings" in market_key:
            period_num = 5
        elif "1st_7_innings" in market_key:
            period_num = 7
        
        # Determine bet type
        if "h2h" in market_key:
            bet_type = f"moneyline_{period_type}_{period_num}"
        elif "spreads" in market_key:
            bet_type = f"spread_{period_type}_{period_num}"
        elif "totals" in market_key:
            bet_type = f"total_{period_type}_{period_num}"
        else:
            bet_type = f"{period_type}_{period_num}"
        
        # Parse based on market type
        if "h2h" in market_key:
            legs.extend(self._parse_h2h_market(outcomes, game, market_key))
            for leg in legs:
                leg["bet_type"] = bet_type
                leg["period"] = period_num
                leg["period_type"] = period_type
        elif "spreads" in market_key:
            legs.extend(self._parse_spread_market(outcomes, game, market_key))
            for leg in legs:
                leg["bet_type"] = bet_type
                leg["period"] = period_num
                leg["period_type"] = period_type
        elif "totals" in market_key:
            legs.extend(self._parse_total_market(outcomes, game, market_key))
            for leg in legs:
                leg["bet_type"] = bet_type
                leg["period"] = period_num
                leg["period_type"] = period_type
        
        return legs
    
    def store_all_markets_as_props(
        self,
        event_data: Dict,
        game: Game
    ):
        """
        Store all markets (alternate spreads, totals, team totals, periods) as PlayerProp-like entries.
        This allows us to store them without modifying the Game model extensively.
        """
        all_markets = self.parse_all_markets_from_event(event_data, game)
        
        # For markets that aren't basic h2h/spread/total, store them
        # We'll create a special prop type for team/period markets
        stored_count = 0
        
        for market_leg in all_markets:
            bet_type = market_leg.get("bet_type", "")
            
            # Skip basic markets (already stored in Game model)
            if bet_type in ["moneyline", "spread", "total", "fighter_moneyline", "boxing_moneyline"]:
                continue
            
            # Store as a special type of prop
            # Use a placeholder player name for team/period markets
            player_name = f"TEAM_{market_leg.get('selection', 'Unknown')}"
            
            # Check if already exists
            existing = self.session.query(PlayerProp).filter_by(
                game_id=game.id,
                player_name=player_name,
                market_key=market_leg.get("market_key"),
                prop_type=bet_type
            ).first()
            
            if not existing:
                prop_value = market_leg.get("total_value") or market_leg.get("spread_value") or market_leg.get("team_total_value")
                
                # Determine over/under from selection
                selection = market_leg.get("selection", "")
                over_odds = market_leg.get("odds") if "Over" in selection else None
                under_odds = market_leg.get("odds") if "Under" in selection else None
                yes_odds = market_leg.get("odds") if not over_odds and not under_odds else None
                
                prop = PlayerProp(
                    game_id=game.id,
                    player_name=player_name,
                    prop_type=bet_type,
                    market_key=market_leg.get("market_key"),
                    description=market_leg.get("description", get_market_description(market_leg.get("market_key", ""))),
                    prop_value=prop_value,
                    over_odds=over_odds,
                    under_odds=under_odds,
                    yes_odds=yes_odds
                )
                self.session.add(prop)
                stored_count += 1
        
        if stored_count > 0:
            try:
                self.session.commit()
                logger.info(f"Stored {stored_count} additional markets for game {game.id}")
            except Exception as e:
                logger.error(f"Error storing additional markets: {e}")
                self.session.rollback()
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

