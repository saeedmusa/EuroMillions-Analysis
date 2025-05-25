"""Client for the Lottery Results API."""
import logging
from typing import Dict, List, Optional, Any
import requests
from datetime import datetime

from ..config import Config

logger = logging.getLogger(__name__)

class LotteryResultsClient:
    """Client for interacting with the Lottery Results API."""
    
    BASE_URL = "https://api.lotteryresultsapi.com/alpha"
    
    def __init__(self, api_token: str = None):
        """Initialize the client with an API token."""
        self.api_token = api_token or Config.LOTTERY_API_TOKEN
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Token': self.api_token,
            'Accept': 'application/json'
        })
    
    def get_latest_draws(self, lottery_tag: str = 'euromillions', limit: int = 5) -> List[Dict[str, Any]]:
        """Get the latest draws for a specific lottery.
        
        Args:
            lottery_tag: The tag of the lottery (default: 'euromillions')
            limit: Maximum number of draws to return (default: 5, max: 5)
            
        Returns:
            List of draw dictionaries with numbers
        """
        # Using the simple numbers endpoint which returns numbers as a string
        endpoint = f"{self.BASE_URL}/lottery/{lottery_tag}/draw/snumbers"
        params = {
            'limit': min(5, max(1, limit)),  # API has a max limit of 5
            'sort_number': False  # Keep original order of numbers
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            
            # The API returns a list of draws with numbers as a space-separated string
            draws = response.json()
            if not isinstance(draws, list):
                logger.error(f"Unexpected API response format: {draws}")
                return []
                
            return draws
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch latest draws: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                try:
                    logger.error(f"Response body: {e.response.text}")
                except:
                    pass
            return []
            
    def get_latest_draw(self, lottery_tag: str = 'euromillions') -> Optional[Dict[str, Any]]:
        """Get the latest draw for a specific lottery.
        
        Args:
            lottery_tag: The tag of the lottery (default: 'euromillions')
            
        Returns:
            Draw dictionary with numbers or None if not found
        """
        endpoint = f"{self.BASE_URL}/lottery/{lottery_tag}/draw/latest/snumbers"
        
        try:
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch latest draw: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
            return None
    
    def get_draw_by_date(self, lottery_tag: str, date: datetime) -> Optional[Dict[str, Any]]:
        """Get a specific draw by date.
        
        Args:
            lottery_tag: The tag of the lottery (e.g., 'euromillions')
            date: The date of the draw
            
        Returns:
            Draw dictionary or None if not found
        """
        date_str = date.strftime('%Y-%m-%d')
        endpoint = f"{self.BASE_URL}/lottery/{lottery_tag}/draw/date/{date_str}"
        
        try:
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch draw for date {date_str}: {e}")
            return None
    
    @staticmethod
    def parse_draw(draw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a draw from the API response into our format.
        
        The API returns data in the format:
        {
            "date": "2023-01-01",
            "numbers": "1 2 3 4 5 6 7"  # First 5 are main numbers, last 2 are lucky stars
        }
        
        Args:
            draw_data: Raw draw data from the API
            
        Returns:
            Parsed draw data or None if invalid
        """
        try:
            # Extract numbers from the space-separated string
            numbers_str = draw_data.get('numbers', '')
            numbers = [int(n) for n in numbers_str.split() if n.isdigit()]
            
            # EuroMillions has 5 main numbers and 2 lucky stars
            if len(numbers) < 7:
                logger.warning(f"Insufficient numbers in draw data. Expected 7, got {len(numbers)}")
                return None
            
            # Parse the date
            date_str = draw_data.get('date')
            if not date_str:
                logger.warning("No date found in draw data")
                return None
                
            try:
                draw_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse date '{date_str}': {e}")
                return None
            
            # Create the draw dictionary
            return {
                'draw_number': 0,  # Not provided in the simple API response
                'draw_date': draw_date,
                'ball1': numbers[0],
                'ball2': numbers[1],
                'ball3': numbers[2],
                'ball4': numbers[3],
                'ball5': numbers[4],
                'lucky_star1': numbers[5],
                'lucky_star2': numbers[6],
                'jackpot': None  # Not provided in the simple API response
            }
            
        except (KeyError, ValueError, AttributeError) as e:
            logger.error(f"Error parsing draw data: {e}")
            logger.debug(f"Problematic draw data: {draw_data}")
            return None
