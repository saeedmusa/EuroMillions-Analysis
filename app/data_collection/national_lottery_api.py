import requests
import logging
from datetime import datetime
from typing import List, Dict, Optional
import time

logger = logging.getLogger(__name__)

class NationalLotteryAPI:
    """Client for the UK National Lottery API."""
    
    BASE_URL = "https://www.national-lottery.co.uk/api/results/v1/euro-millions"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
        })
    
    def get_draws(self, size: int = 100, page: int = 0) -> List[Dict]:
        """Get a list of EuroMillions draws."""
        url = f"{self.BASE_URL}/draws?size={size}&page={page}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, dict) or 'content' not in data:
                logger.error(f"Unexpected API response format: {data}")
                return []
                
            return data['content']
            
        except Exception as e:
            logger.error(f"Error fetching draws: {e}")
            return []
    
    def get_all_draws(self) -> List[Dict]:
        """Get all available EuroMillions draws."""
        all_draws = []
        page = 0
        size = 100  # Max allowed by the API
        
        while True:
            logger.info(f"Fetching page {page + 1} of draws...")
            draws = self.get_draws(size=size, page=page)
            
            if not draws:
                break
                
            all_draws.extend(draws)
            
            # If we got fewer results than requested, we've reached the end
            if len(draws) < size:
                break
                
            page += 1
            time.sleep(1)  # Be nice to the API
            
        return all_draws
    
    @staticmethod
    def parse_draw(draw_data: Dict) -> Optional[Dict]:
        """Parse a draw from the API response into our format."""
        try:
            # Extract main numbers
            main_numbers = draw_data.get('mainNumbers', [])
            if len(main_numbers) != 5:
                return None
                
            # Extract lucky stars
            lucky_stars = draw_data.get('luckyStars', [])
            if len(lucky_stars) != 2:
                return None
                
            # Parse date
            draw_date = datetime.strptime(draw_data['drawDate'], '%Y-%m-%dT%H:%M:%S%z').date()
            
            return {
                'draw_number': int(draw_data['drawNumber']),
                'draw_date': draw_date,
                'ball1': main_numbers[0],
                'ball2': main_numbers[1],
                'ball3': main_numbers[2],
                'ball4': main_numbers[3],
                'ball5': main_numbers[4],
                'lucky_star1': lucky_stars[0],
                'lucky_star2': lucky_stars[1],
                'jackpot': float(draw_data.get('prizeTiers', [{}])[0].get('prizeAmount', 0)) if draw_data.get('prizeTiers') else None
            }
            
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Error parsing draw data: {e}")
            return None
