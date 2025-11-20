"""RapidAPI Sportsbook API integration."""
import requests
from typing import List, Dict, Optional
from config import RAPIDAPI_KEY, RAPIDAPI_SPORTSBOOK_BASE_URL, RAPIDAPI_SPORTSBOOK_HOST
import logging

logger = logging.getLogger(__name__)


class RapidAPISportsbook:
    """Interface for RapidAPI Sportsbook API."""
    
    def __init__(self):
        self.api_key = RAPIDAPI_KEY
        self.base_url = RAPIDAPI_SPORTSBOOK_BASE_URL
        self.host = RAPIDAPI_SPORTSBOOK_HOST
        self.headers = {
            'x-rapidapi-host': self.host,
            'x-rapidapi-key': self.api_key
        }
    
    def get_advantages(self, params: Optional[Dict] = None) -> List[Dict]:
        """Get betting advantages/edges from the API.
        
        Args:
            params: Optional query parameters (sport, league, etc.)
        
        Returns:
            List of advantage/edge opportunities
        """
        url = f"{self.base_url}/v1/advantages/"
        
        try:
            response = requests.get(url, headers=self.headers, params=params or {})
            response.raise_for_status()
            data = response.json()
            
            # Handle different response formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Check for common response wrapper keys
                if 'data' in data:
                    return data['data']
                elif 'advantages' in data:
                    return data['advantages']
                elif 'results' in data:
                    return data['results']
                else:
                    # Return as single item in list
                    return [data]
            else:
                logger.warning(f"Unexpected response format: {type(data)}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching advantages from RapidAPI: {e}")
            return []
    
    def get_advantages_by_sport(self, sport: str) -> List[Dict]:
        """Get advantages filtered by sport.
        
        Args:
            sport: Sport name (e.g., 'nba', 'nfl', 'mlb')
        
        Returns:
            List of advantages for the sport
        """
        params = {'sport': sport.lower()}
        return self.get_advantages(params)
    
    def get_advantages_by_league(self, league: str) -> List[Dict]:
        """Get advantages filtered by league.
        
        Args:
            league: League name
        
        Returns:
            List of advantages for the league
        """
        params = {'league': league}
        return self.get_advantages(params)
    
    def parse_advantage_to_value_bet(self, advantage: Dict) -> Optional[Dict]:
        """Convert API advantage data to value bet format.
        
        Args:
            advantage: Advantage data from API
        
        Returns:
            Value bet dictionary or None
        """
        try:
            # Extract relevant fields (adjust based on actual API response structure)
            return {
                'game_id': advantage.get('game_id') or advantage.get('id'),
                'sport': advantage.get('sport'),
                'league': advantage.get('league'),
                'team': advantage.get('team') or advantage.get('selection'),
                'bet_type': advantage.get('bet_type') or advantage.get('market'),
                'odds': advantage.get('odds') or advantage.get('price'),
                'edge': advantage.get('edge') or advantage.get('advantage') or advantage.get('value'),
                'confidence': advantage.get('confidence') or 0.7,
                'bookmaker': advantage.get('bookmaker') or advantage.get('sportsbook'),
                'description': advantage.get('description') or advantage.get('reason'),
                'raw_data': advantage
            }
        except Exception as e:
            logger.error(f"Error parsing advantage: {e}")
            return None
    
    def get_value_bets(self, sport: Optional[str] = None, min_edge: float = 0.0) -> List[Dict]:
        """Get value bets from advantages API.
        
        Args:
            sport: Optional sport filter
            min_edge: Minimum edge/advantage percentage
        
        Returns:
            List of value bet dictionaries
        """
        params = {}
        if sport:
            params['sport'] = sport.lower()
        
        advantages = self.get_advantages(params)
        value_bets = []
        
        for adv in advantages:
            value_bet = self.parse_advantage_to_value_bet(adv)
            if value_bet:
                edge = value_bet.get('edge', 0)
                if isinstance(edge, str):
                    # Try to parse percentage string
                    try:
                        edge = float(edge.replace('%', ''))
                    except:
                        edge = 0
                
                if edge >= min_edge:
                    value_bets.append(value_bet)
        
        return value_bets

