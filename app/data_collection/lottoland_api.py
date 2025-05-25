import requests
import logging
from datetime import datetime
from typing import List, Dict, Optional
import time

logger = logging.getLogger(__name__)

class LottolandAPI:
    """Client for the Lottoland API."""
    
    BASE_URL = "https://www.lottoland.com/api/drawings/euroMillions"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
        })
    
    def get_latest_draws(self, limit: int = 100) -> List[Dict]:
        """Get the latest EuroMillions draws."""
        url = f"{self.BASE_URL}?limit={limit}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, dict) or 'items' not in data:
                logger.error(f"Unexpected API response format: {data}")
                return []
                
            return data['items']
            
        except Exception as e:
            logger.error(f"Error fetching draws: {e}")
            return []
    
    @staticmethod
    def parse_draw(draw_data: Dict) -> Optional[Dict]:
        """Parse a draw from the API response into our format."""
        try:
            # Extract main numbers
            main_numbers = draw_data.get('numbers', [])
            if len(main_numbers) != 5:
                return None
                
            # Extract lucky stars (called 'euros' in this API)
            lucky_stars = draw_data.get('euros', [])
            if len(lucky_stars) != 2:
                return None
                
            # Parse date
            draw_date = datetime.fromisoformat(draw_data['date'].replace('Z', '+00:00')).date()
            
            return {
                'draw_number': int(draw_data['draw_id']),
                'draw_date': draw_date,
                'ball1': main_numbers[0],
                'ball2': main_numbers[1],
                'ball3': main_numbers[2],
                'ball4': main_numbers[3],
                'ball5': main_numbers[4],
                'lucky_star1': lucky_stars[0],
                'lucky_star2': lucky_stars[1],
                'jackpot': float(draw_data.get('prize', 0)) / 100  # Convert cents to euros
            }
            
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Error parsing draw data: {e}")
            return None
