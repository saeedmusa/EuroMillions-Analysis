import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
from typing import List, Dict, Optional
import time
import random

logger = logging.getLogger(__name__)

class EuroMillionsScraper:
    """Scraper for EuroMillions draw history."""
    
    BASE_URL = "https://www.euro-millions.com/results-archive-{year}"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    def __init__(self, start_year: int = 2004):
        self.start_year = start_year
        self.current_year = datetime.now().year
    
    def _get_page_content(self, url: str) -> Optional[str]:
        """Fetch page content with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.HEADERS, timeout=10)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                    return None
                time.sleep(random.uniform(1, 3))  # Random delay between retries
    
    def _parse_draw(self, row) -> Optional[Dict]:
        """Parse a single draw row from the results table."""
        try:
            cells = row.find_all('td')
            if len(cells) < 3:  # Ensure we have enough cells
                return None
                
            # Extract draw date
            date_str = cells[0].get_text(strip=True)
            draw_date = datetime.strptime(date_str, '%d %b %Y').date()
            
            # Extract draw number
            draw_number = int(cells[1].get_text(strip=True))
            
            # Extract balls
            balls = [int(span.get_text(strip=True)) for span in cells[2].find_all('span', class_='ball')]
            if len(balls) != 5:
                return None
                
            # Extract lucky stars
            stars = [int(span.get_text(strip=True)) for span in cells[2].find_all('span', class_='lucky-star')]
            if len(stars) != 2:
                return None
            
            # Extract jackpot (if available)
            jackpot = None
            if len(cells) > 3:
                try:
                    jackpot_str = cells[3].get_text(strip=True).replace('€', '').replace(',', '')
                    jackpot = float(jackpot_str)
                except (ValueError, AttributeError):
                    pass
            
            return {
                'draw_number': draw_number,
                'draw_date': draw_date,
                'ball1': balls[0],
                'ball2': balls[1],
                'ball3': balls[2],
                'ball4': balls[3],
                'ball5': balls[4],
                'lucky_star1': stars[0],
                'lucky_star2': stars[1],
                'jackpot': jackpot
            }
            
        except (ValueError, AttributeError) as e:
            logger.error(f"Error parsing draw row: {e}")
            return None
    
    def scrape_year(self, year: int) -> List[Dict]:
        """Scrape all draws for a specific year."""
        url = self.BASE_URL.format(year=year)
        logger.info(f"Scraping {url}")
        
        content = self._get_page_content(url)
        if not content:
            return []
            
        soup = BeautifulSoup(content, 'html.parser')
        table = soup.find('table', {'class': 'results-table'})
        if not table:
            logger.warning(f"No results table found for year {year}")
            return []
            
        draws = []
        for row in table.find_all('tr')[1:]:  # Skip header row
            draw = self._parse_draw(row)
            if draw:
                draws.append(draw)
                
        return draws
    
    def scrape_all(self) -> List[Dict]:
        """Scrape all available years of draw history."""
        all_draws = []
        for year in range(self.start_year, self.current_year + 1):
            draws = self.scrape_year(year)
            all_draws.extend(draws)
            # Be nice to the server
            time.sleep(random.uniform(0.5, 1.5))
            
        return all_draws
