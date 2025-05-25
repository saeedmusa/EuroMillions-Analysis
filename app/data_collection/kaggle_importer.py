"""
EuroMillions data importer from Kaggle dataset.

This script downloads and imports EuroMillions historical data from Kaggle.
"""
import os
import logging
import tempfile
import csv
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.base import Draw
from app.config import Config

logger = logging.getLogger(__name__)

# Kaggle dataset URL for EuroMillions data
KAGGLE_DATASET_URL = "https://storage.googleapis.com/kaggle-data-sets/1368/2352/bundle/archive.zip?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=gcp-kaggle-com%40kaggle-161607.iam.gserviceaccount.com%2F20230801%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20230801T040952Z&X-Goog-Expires=259200&X-Goog-SignedHeaders=host&X-Goog-Signature=a88b6017e3a7b0b9a6f42f0680bd32a46eaa2c7ff77fe0b4c4bd60e8e8837d3c3c95fc5c2e8ccedbc8e6d7d8e5cc5a60ce4dc6e8bd8c81ec7b8a3fae55b17a46ee5e9c16bf4cf5f2c1b651c76a675f45bf4fc0e53c2e68a2f87b30ac4a24c2fa9a1b5f8add75eb5b7be8e0ee12a7d7c1d4e0ed3c57fad8b5dc2c0c7e2c1db9debb9d8c2d0c2d9c2d5c2d3d3d9c2"

# Alternative URL: direct CSV of historical results
DIRECT_CSV_URL = "https://www.nationallottery.co.uk/c/files/euromillions-draw-history.csv"

def download_file(url: str, local_filename: str) -> Optional[str]:
    """Download a file from a URL.
    
    Args:
        url: URL to download
        local_filename: Path to save the file
        
    Returns:
        Path to the downloaded file or None if download failed
    """
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return local_filename
    except Exception as e:
        logger.error(f"Error downloading file from {url}: {e}")
        return None

def parse_euromillions_csv(csv_path: str) -> List[Dict[str, Any]]:
    """Parse EuroMillions CSV file.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        List of draw dictionaries
    """
    draws = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Try to parse the CSV data based on different possible formats
                try:
                    # Format 1: National Lottery format
                    if 'DrawDate' in row and 'Ball 1' in row:
                        draw_date = datetime.strptime(row['DrawDate'], '%d-%b-%Y').date()
                        draw = {
                            'draw_date': draw_date,
                            'ball1': int(row['Ball 1']),
                            'ball2': int(row['Ball 2']),
                            'ball3': int(row['Ball 3']),
                            'ball4': int(row['Ball 4']),
                            'ball5': int(row['Ball 5']),
                            'lucky_star1': int(row['Lucky Star 1']),
                            'lucky_star2': int(row['Lucky Star 2']),
                            'jackpot': float(row.get('Jackpot', 0)) if row.get('Jackpot') else None
                        }
                        draws.append(draw)
                    # Format 2: Kaggle dataset format
                    elif 'date' in row and 'n1' in row:
                        draw_date = datetime.strptime(row['date'], '%Y-%m-%d').date()
                        draw = {
                            'draw_date': draw_date,
                            'ball1': int(row['n1']),
                            'ball2': int(row['n2']),
                            'ball3': int(row['n3']),
                            'ball4': int(row['n4']),
                            'ball5': int(row['n5']),
                            'lucky_star1': int(row['e1']),
                            'lucky_star2': int(row['e2']),
                            'jackpot': float(row.get('gain', 0)) if row.get('gain') else None
                        }
                        draws.append(draw)
                    # Format 3: Alternative format with different column names
                    elif any(f'Ball_{i}' in row for i in range(1, 6)):
                        # Extract date from various possible formats
                        date_field = next((f for f in row.keys() if 'date' in f.lower()), None)
                        if date_field and row[date_field]:
                            # Try different date formats
                            for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
                                try:
                                    draw_date = datetime.strptime(row[date_field], fmt).date()
                                    break
                                except ValueError:
                                    continue
                            else:
                                logger.warning(f"Could not parse date: {row[date_field]}")
                                continue
                                
                            # Try to identify ball and star columns
                            balls = []
                            stars = []
                            
                            # Look for columns with 'Ball' or 'Number' in the name
                            for i in range(1, 10):  # Check more than 5 in case of variations
                                for prefix in ['Ball_', 'Ball ', 'Number_', 'Number ']:
                                    col = f"{prefix}{i}"
                                    if col in row and row[col] and row[col].isdigit():
                                        balls.append(int(row[col]))
                                        if len(balls) == 5:
                                            break
                                
                            # Look for columns with 'Star' or 'Lucky' in the name
                            for i in range(1, 5):  # Check more than 2 in case of variations
                                for prefix in ['Star_', 'Star ', 'Lucky_', 'Lucky Star_', 'Lucky Star ']:
                                    col = f"{prefix}{i}"
                                    if col in row and row[col] and row[col].isdigit():
                                        stars.append(int(row[col]))
                                        if len(stars) == 2:
                                            break
                            
                            # If we found 5 balls and 2 stars, create the draw
                            if len(balls) >= 5 and len(stars) >= 2:
                                draw = {
                                    'draw_date': draw_date,
                                    'ball1': balls[0],
                                    'ball2': balls[1],
                                    'ball3': balls[2],
                                    'ball4': balls[3],
                                    'ball5': balls[4],
                                    'lucky_star1': stars[0],
                                    'lucky_star2': stars[1],
                                    'jackpot': None  # Often not available in these formats
                                }
                                draws.append(draw)
                except Exception as e:
                    logger.error(f"Error parsing row: {e}")
                    continue
                    
        logger.info(f"Successfully parsed {len(draws)} draws from CSV")
        return draws
    except Exception as e:
        logger.error(f"Error parsing CSV file: {e}")
        return []

def import_kaggle_data() -> int:
    """Import EuroMillions data from Kaggle dataset.
    
    Returns:
        Number of draws imported
    """
    logger.info("Starting import of EuroMillions data from Kaggle dataset...")
    
    # Create temporary directory for downloaded files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Try direct CSV URL first
        csv_path = os.path.join(temp_dir, "euromillions.csv")
        logger.info(f"Downloading EuroMillions data from {DIRECT_CSV_URL}...")
        
        if download_file(DIRECT_CSV_URL, csv_path):
            logger.info("Successfully downloaded EuroMillions data")
            draws = parse_euromillions_csv(csv_path)
            
            if not draws:
                logger.warning("No draws found in the downloaded CSV file")
                return 0
                
            return save_draws_to_database(draws)
        else:
            logger.error("Failed to download EuroMillions data")
            return 0

def save_draws_to_database(draws: List[Dict[str, Any]]) -> int:
    """Save parsed draws to the database.
    
    Args:
        draws: List of draw dictionaries
        
    Returns:
        Number of draws imported
    """
    logger.info(f"Saving {len(draws)} draws to the database...")
    
    db = SessionLocal()
    try:
        imported_count = 0
        
        # Sort draws by date to ensure consistent import
        draws.sort(key=lambda x: x['draw_date'])
        
        for draw_data in draws:
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
                logger.debug(f"Imported draw for date {draw_data['draw_date']}")
            except Exception as e:
                db.rollback()
                logger.error(f"Error importing draw for date {draw_data['draw_date']}: {e}")
        
        # Get database statistics
        total_draws = db.query(Draw).count()
        earliest_draw = db.query(Draw).order_by(Draw.draw_date.asc()).first()
        latest_draw = db.query(Draw).order_by(Draw.draw_date.desc()).first()
        
        logger.info(f"Import completed successfully. Imported {imported_count} new draws.")
        logger.info(f"Database now contains {total_draws} draws in total.")
        
        if earliest_draw and latest_draw:
            logger.info(f"Date range: {earliest_draw.draw_date} to {latest_draw.draw_date}")
            
        # Print a summary to the console as well
        print(f"\nImport completed successfully!")
        print(f"- Imported {imported_count} new draws")
        print(f"- Database now contains {total_draws} total draws")
        if earliest_draw and latest_draw:
            print(f"- Date range: {earliest_draw.draw_date} to {latest_draw.draw_date}")
            
        return imported_count
    finally:
        db.close()

if __name__ == "__main__":
    import_kaggle_data()
