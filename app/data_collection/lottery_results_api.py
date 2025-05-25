import logging
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime

from ..config import Config

logger = logging.getLogger(__name__)

class LotteryResultsAPI:
    """Client for the Lottery Results API."""
    
    def __init__(self, api_token: str = None):
        """Initialize the API client.
        
        Args:
            api_token: Optional API token. If not provided, will use LOTTERY_API_TOKEN from config.
        """
        self.base_url = Config.LOTTERY_API_BASE_URL
        self.api_token = api_token or Config.LOTTERY_API_TOKEN
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Token': self.api_token,
            'Accept': 'application/json',
            'User-Agent': 'EuroMillionsAnalysis/1.0'
        })
    
    def get_latest_draw(self) -> Optional[Dict[str, Any]]:
        """Get the latest EuroMillions draw."""
        endpoint = f"{self.base_url}/euromillions/draw/latest"
        return self._make_request(endpoint)
    
    def get_draws(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get a list of EuroMillions draws.
        
        Args:
            limit: Maximum number of draws to return (default: 100, max: 1000)
            offset: Number of draws to skip (for pagination)
            
        Returns:
            List of draw dictionaries
        """
        endpoint = f"{self.base_url}/euromillions/draws"
        params = {
            'limit': min(1000, max(1, limit)),
            'offset': max(0, offset)
        }
        return self._make_request(endpoint, params=params) or []
    
    def get_draw_by_date(self, date: datetime) -> Optional[Dict[str, Any]]:
        """Get a EuroMillions draw by date.
        
        Args:
            date: Date of the draw
            
        Returns:
            Draw dictionary or None if not found
        """
        date_str = date.strftime('%Y-%m-%d')
        endpoint = f"{self.base_url}/euromillions/draw/date/{date_str}"
        return self._make_request(endpoint)
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Any:
        """Make an API request.
        
        Args:
            url: Full API endpoint URL
            params: Query parameters
            
        Returns:
            Parsed JSON response or None if request failed
        """
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return None
    
    @staticmethod
    def parse_draw(draw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a draw from the API response into our format."""
        try:
            # Extract main numbers and lucky stars
            numbers = draw_data.get('numbers', [])
            if len(numbers) < 7:  # 5 main numbers + 2 lucky stars
                return None
                
            return {
                'draw_number': int(draw_data.get('drawNumber', '0')),
                'draw_date': datetime.strptime(draw_data['date'], '%Y-%m-%d').date(),
                'ball1': numbers[0],
                'ball2': numbers[1],
                'ball3': numbers[2],
                'ball4': numbers[3],
                'ball5': numbers[4],
                'lucky_star1': numbers[5],
                'lucky_star2': numbers[6],
                'jackpot': float(draw_data.get('prizeFund', {}).get('value', 0)) if draw_data.get('prizeFund') else None
            }
        except (KeyError, ValueError, IndexError, TypeError) as e:
            logger.error(f"Error parsing draw data: {e}")
            return None
