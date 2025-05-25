"""
Historical EuroMillions data importer.

This script scrapes historical EuroMillions draw data and imports it into our database.
Adapted from the euromillions-api project by Pedro Mealha.
"""
import os
import requests
import logging
import time
import random
from datetime import datetime, date
from typing import List, Dict, Any, Tuple, Optional
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.base import Draw
from app.config import Config

logger = logging.getLogger(__name__)

# Base URL for scraping EuroMillions results
EUROMILLIONS_WEB_BASE_URL = "https://www.euro-millions.com"
EUROMILLIONS_MIN_YEAR = 2004  # EuroMillions started in February 2004


def get_random_user_agent() -> str:
    """Return a random user agent string to avoid detection."""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
    ]
    return random.choice(user_agents)

def get_draws_by_year(year: int) -> list:
    """Fetch all EuroMillions draws for a specific year.
    
    Args:
        year: The year to fetch draws for
        
    Returns:
        A list of HTML elements containing draw data
    """
    # Alternative URLs to try if the primary one fails
    urls_to_try = [
        f"{EUROMILLIONS_WEB_BASE_URL}/results-history-{year}",
        f"https://www.lottery.co.uk/euromillions/results/archive-{year}",
        f"https://www.national-lottery.co.uk/results/euromillions/draw-history/{year}"
    ]
    
    for url_index, url in enumerate(urls_to_try):
        try:
            # Set up headers to mimic a real browser
            headers = {
                "User-Agent": get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            }
            
            # Add a delay to avoid rate limiting
            time.sleep(2 + random.random() * 3)  # Random delay between 2-5 seconds
            
            logger.info(f"Trying URL {url_index+1}/{len(urls_to_try)}: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            html = BeautifulSoup(response.content, 'html.parser')
            
            # Try different selectors based on the website structure
            if url_index == 0:  # euro-millions.com
                content = html.find(id='content')
                if not content:
                    logger.warning(f"Could not find content section for year {year} at {url}")
                    continue
                    
                tbody = content.find('tbody')
                if not tbody:
                    logger.warning(f"Could not find table body for year {year} at {url}")
                    continue
                    
                draws = tbody.find_all('tr', class_='resultRow')
                if not draws:
                    logger.warning(f"No draws found for year {year} at {url}")
                    continue
                
                draws.reverse()  # Sort by date ascending
                logger.info(f"Successfully found {len(draws)} draws for year {year} at {url}")
                return draws
            elif url_index == 1:  # lottery.co.uk
                # Implement parsing for lottery.co.uk if needed
                pass
            elif url_index == 2:  # national-lottery.co.uk
                # Implement parsing for national-lottery.co.uk if needed
                pass
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching draws for year {year} from {url}: {e}")
            # Continue to the next URL
            
    # If we tried all URLs and none worked, return an empty list
    logger.error(f"All attempts to fetch draws for year {year} failed")
    return []


def get_date(details_route: str) -> date:
    """Extract the date from a details route.
    
    Args:
        details_route: The URL path to the draw details
        
    Returns:
        The draw date
    """
    date_str = details_route.split('/')[2]
    parsed_date = datetime.strptime(date_str, '%d-%m-%Y')
    return parsed_date.date()


def get_numbers(html) -> List[int]:
    """Extract the main numbers from HTML.
    
    Args:
        html: BeautifulSoup HTML element
        
    Returns:
        List of drawn numbers
    """
    numbers = []
    balls = html.find_all('li', class_='ball')
    
    if not balls or balls[0].text == '-':
        return numbers
        
    for ball in balls:
        try:
            numbers.append(int(ball.text))
        except (ValueError, TypeError):
            pass
            
    return numbers


def get_stars(html) -> List[int]:
    """Extract the lucky stars from HTML.
    
    Args:
        html: BeautifulSoup HTML element
        
    Returns:
        List of lucky stars
    """
    stars = []
    balls_star = html.find_all('li', class_='lucky-star')
    
    if not balls_star or balls_star[0].text == '-':
        return stars
        
    for ball_star in balls_star:
        try:
            stars.append(int(ball_star.text))
        except (ValueError, TypeError):
            pass
            
    return stars


def get_details(details_route: str) -> Tuple[List[Dict[str, Any]], bool]:
    """Get detailed information about a draw.
    
    Args:
        details_route: The URL path to the draw details
        
    Returns:
        A tuple containing the list of prizes and whether there was a jackpot winner
    """
    url = f"{EUROMILLIONS_WEB_BASE_URL}{details_route}"
    
    try:
        page = requests.get(url, timeout=10)
        page.raise_for_status()
        
        html = BeautifulSoup(page.content, 'html.parser')
        
        prizes = []
        has_winner = False
        
        body = html.find(id="PrizePT")
        body = body if body is not None else html.find(id="PrizeES")
        
        if body is None:
            return [], False
            
        rows = body.find('tbody')
        if rows is None:
            return [], False
            
        rows = rows.find_all('tr')
        if len(rows) == 0:
            return [], False
            
        for row in rows:
            if row.find('td').text.replace(' ', '').strip() == 'Totals':
                continue
                
            prize = {
                "prize": 0,
                "winners": 0,
                "combination": ""
            }
            
            columns = row.find_all('td')
            for column in columns:
                if 'data-title' not in column.attrs:
                    continue
                    
                if column['data-title'] == 'Numbers Matched':
                    value = column.text.replace(' ', '').strip()
                    if len(value) == 1:
                        value = f"{value}+0"
                    prize['combination'] = value
                elif column['data-title'] == 'Prize Per Winner':
                    try:
                        prize['prize'] = float(column.text.replace(',', '').replace('€', '').strip())
                    except (ValueError, TypeError):
                        prize['prize'] = 0
                elif column['data-title'] == 'Total Winners':
                    winners_text = column.text.replace(',', '').replace('Rollover! ', '').replace('Rolldown! ', '').strip()
                    try:
                        prize['winners'] = int(winners_text)
                    except (ValueError, TypeError):
                        prize['winners'] = 0
                        
            if prize['combination'] == "5+2" and prize['winners'] > 0:
                has_winner = True
                
            prizes.append(prize)
            
        return prizes, has_winner
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching draw details for {details_route}: {e}")
        return [], False


def parse_draw(draw_html) -> Optional[Dict[str, Any]]:
    """Parse a draw HTML element into a dictionary.
    
    Args:
        draw_html: BeautifulSoup HTML element for a draw
        
    Returns:
        Dictionary containing draw data or None if parsing failed
    """
    try:
        data = draw_html.find('td').find('a')
        if not data or 'href' not in data.attrs:
            return None
            
        details_route = data['href']
        
        # Get draw date
        draw_date = get_date(details_route)
        
        # Get numbers and stars
        numbers = get_numbers(draw_html)
        stars = get_stars(draw_html)
        
        if len(numbers) != 5 or len(stars) != 2:
            logger.warning(f"Invalid number of balls or stars for draw on {draw_date}")
            return None
            
        # Get prize information
        prizes, has_winner = get_details(details_route)
        
        # Find jackpot prize
        jackpot = None
        for prize in prizes:
            if prize['combination'] == "5+2":
                jackpot = prize['prize']
                break
                
        return {
            'draw_date': draw_date,
            'ball1': numbers[0],
            'ball2': numbers[1],
            'ball3': numbers[2],
            'ball4': numbers[3],
            'ball5': numbers[4],
            'lucky_star1': stars[0],
            'lucky_star2': stars[1],
            'jackpot': jackpot
        }
    except Exception as e:
        logger.error(f"Error parsing draw: {e}")
        return None


def import_year(year: int, db: Session) -> int:
    """Import all draws for a specific year.
    
    Args:
        year: The year to import
        db: Database session
        
    Returns:
        Number of draws imported
    """
    logger.info(f"Importing draws for year {year}...")
    
    draws_html = get_draws_by_year(year)
    
    if not draws_html:
        logger.warning(f"No draws found for year {year}")
        return 0
        
    logger.info(f"Found {len(draws_html)} draws for year {year}")
    
    imported_count = 0
    for draw_html in draws_html:
        draw_data = parse_draw(draw_html)
        
        if not draw_data:
            continue
            
        # Check if draw already exists
        existing_draw = db.query(Draw).filter(Draw.draw_date == draw_data['draw_date']).first()
        if existing_draw:
            logger.debug(f"Draw for date {draw_data['draw_date']} already exists, skipping")
            continue
            
        # Create new draw
        draw = Draw(**draw_data)
        db.add(draw)
        
        try:
            db.commit()
            imported_count += 1
            logger.info(f"Imported draw for date {draw_data['draw_date']}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error importing draw for date {draw_data['draw_date']}: {e}")
    
    return imported_count


def import_all_historical_data() -> int:
    """Import all historical EuroMillions draws.
    
    Returns:
        Total number of draws imported
    """
    logger.info("Starting import of all historical EuroMillions draws...")
    
    db = SessionLocal()
    try:
        current_year = datetime.now().year
        total_imported = 0
        
        # Process years in reverse order (newest first)
        # This ensures we get the most recent data even if the scraping is interrupted
        for year in range(current_year, EUROMILLIONS_MIN_YEAR - 1, -1):
            logger.info(f"Processing year {year}...")
            year_imported = import_year(year, db)
            total_imported += year_imported
            
            # Add a longer delay between years to avoid triggering anti-scraping measures
            if year > EUROMILLIONS_MIN_YEAR:
                delay = 5 + random.random() * 5  # Random delay between 5-10 seconds
                logger.info(f"Waiting {delay:.2f} seconds before processing next year...")
                time.sleep(delay)
                
        # Get database statistics
        total_draws = db.query(Draw).count()
        earliest_draw = db.query(Draw).order_by(Draw.draw_date.asc()).first()
        latest_draw = db.query(Draw).order_by(Draw.draw_date.desc()).first()
        
        logger.info(f"Import completed successfully. Imported {total_imported} new draws.")
        logger.info(f"Database now contains {total_draws} draws in total.")
        
        if earliest_draw and latest_draw:
            logger.info(f"Date range: {earliest_draw.draw_date} to {latest_draw.draw_date}")
        
        # Print a summary to the console as well
        print(f"\nImport completed successfully!")
        print(f"- Imported {total_imported} new draws")
        print(f"- Database now contains {total_draws} total draws")
        if earliest_draw and latest_draw:
            print(f"- Date range: {earliest_draw.draw_date} to {latest_draw.draw_date}")
            
        return total_imported
    finally:
        db.close()


if __name__ == "__main__":
    import_all_historical_data()
