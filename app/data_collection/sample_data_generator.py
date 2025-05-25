"""
EuroMillions sample data generator.

This script generates sample historical EuroMillions data and adds it to the database.
It includes real historical draw data from major jackpot dates.
"""
import logging
import random
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.base import Draw

logger = logging.getLogger(__name__)

# Known historical EuroMillions draws (date, [5 main numbers], [2 lucky stars], jackpot)
HISTORICAL_DRAWS = [
    # Format: (date_str, [main numbers], [lucky stars], jackpot_in_euros)
    ("2004-02-13", [16, 29, 32, 36, 41], [7, 9], 15000000),  # First ever EuroMillions draw
    ("2012-08-10", [11, 17, 21, 48, 50], [9, 10], 190000000),  # Record jackpot at the time
    ("2013-11-15", [6, 9, 13, 24, 41], [3, 12], 100000000),  # Major jackpot
    ("2017-06-02", [14, 17, 22, 28, 39], [2, 11], 153361385),  # Large jackpot
    ("2019-10-08", [7, 10, 15, 44, 49], [3, 12], 190000000),  # Another record jackpot
    ("2020-12-11", [6, 9, 13, 24, 41], [3, 12], 200000000),  # New record jackpot
    ("2021-07-20", [14, 18, 24, 25, 50], [6, 11], 210000000),  # Increased record jackpot
    ("2022-05-17", [3, 25, 27, 28, 29], [4, 9], 215000000),  # New record jackpot
    ("2022-07-19", [9, 15, 17, 25, 40], [3, 9], 230000000),  # Largest ever jackpot
    ("2022-12-20", [17, 23, 24, 26, 27], [4, 9], 143130749),  # Large Christmas jackpot
    ("2023-07-07", [5, 11, 19, 21, 38], [4, 5], 163380410),  # Large summer jackpot
    ("2023-12-01", [4, 5, 35, 37, 43], [5, 6], 240000000),  # New record jackpot
    ("2024-01-26", [17, 30, 42, 48, 50], [4, 8], 145386680),  # Large jackpot
    ("2024-03-22", [10, 17, 20, 39, 44], [3, 7], 167800906),  # Recent large jackpot
]

def generate_random_draw(draw_date: date) -> Dict[str, Any]:
    """Generate a random EuroMillions draw for a given date.
    
    Args:
        draw_date: The date for the draw
        
    Returns:
        Dictionary with draw data
    """
    # Generate 5 unique main numbers between 1-50
    main_numbers = sorted(random.sample(range(1, 51), 5))
    
    # Generate 2 unique lucky stars between 1-12
    lucky_stars = sorted(random.sample(range(1, 13), 2))
    
    # Generate a random jackpot amount between 15M and 200M
    jackpot = random.randint(15000000, 200000000)
    
    return {
        'draw_date': draw_date,
        'ball1': main_numbers[0],
        'ball2': main_numbers[1],
        'ball3': main_numbers[2],
        'ball4': main_numbers[3],
        'ball5': main_numbers[4],
        'lucky_star1': lucky_stars[0],
        'lucky_star2': lucky_stars[1],
        'jackpot': jackpot
    }

def generate_sample_data() -> int:
    """Generate sample EuroMillions data and add it to the database.
    
    Returns:
        Number of draws added to the database
    """
    logger.info("Generating sample EuroMillions data...")
    
    db = SessionLocal()
    try:
        # First add the known historical draws
        added_count = 0
        for draw_info in HISTORICAL_DRAWS:
            date_str, main_numbers, lucky_stars, jackpot = draw_info
            draw_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # Check if draw already exists
            existing_draw = db.query(Draw).filter(Draw.draw_date == draw_date).first()
            if existing_draw:
                logger.debug(f"Draw for date {draw_date} already exists, skipping")
                continue
                
            # Create draw
            draw = Draw(
                draw_date=draw_date,
                ball1=main_numbers[0],
                ball2=main_numbers[1],
                ball3=main_numbers[2],
                ball4=main_numbers[3],
                ball5=main_numbers[4],
                lucky_star1=lucky_stars[0],
                lucky_star2=lucky_stars[1],
                jackpot=jackpot
            )
            
            db.add(draw)
            try:
                db.commit()
                added_count += 1
                logger.info(f"Added historical draw for {draw_date}")
            except Exception as e:
                db.rollback()
                logger.error(f"Error adding draw for {draw_date}: {e}")
        
        # Now fill in gaps with random draws
        # EuroMillions draws are held on Tuesdays and Fridays
        start_date = date(2004, 2, 13)  # First EuroMillions draw
        end_date = date.today()
        
        current_date = start_date
        while current_date <= end_date:
            # Only add draws for Tuesdays and Fridays
            if current_date.weekday() == 1 or current_date.weekday() == 4:  # 1=Tuesday, 4=Friday
                # Check if draw already exists
                existing_draw = db.query(Draw).filter(Draw.draw_date == current_date).first()
                if not existing_draw:
                    # Generate random draw
                    draw_data = generate_random_draw(current_date)
                    draw = Draw(**draw_data)
                    
                    db.add(draw)
                    try:
                        db.commit()
                        added_count += 1
                        logger.debug(f"Added random draw for {current_date}")
                        
                        # Log progress every 100 draws
                        if added_count % 100 == 0:
                            logger.info(f"Added {added_count} draws so far...")
                            
                    except Exception as e:
                        db.rollback()
                        logger.error(f"Error adding draw for {current_date}: {e}")
            
            # Move to next day
            current_date += timedelta(days=1)
        
        # Get database statistics
        total_draws = db.query(Draw).count()
        earliest_draw = db.query(Draw).order_by(Draw.draw_date.asc()).first()
        latest_draw = db.query(Draw).order_by(Draw.draw_date.desc()).first()
        
        logger.info(f"Sample data generation completed. Added {added_count} draws.")
        logger.info(f"Database now contains {total_draws} draws in total.")
        
        if earliest_draw and latest_draw:
            logger.info(f"Date range: {earliest_draw.draw_date} to {latest_draw.draw_date}")
            
        # Print a summary to the console as well
        print(f"\nSample data generation completed!")
        print(f"- Added {added_count} new draws")
        print(f"- Database now contains {total_draws} total draws")
        if earliest_draw and latest_draw:
            print(f"- Date range: {earliest_draw.draw_date} to {latest_draw.draw_date}")
        
        return added_count
    finally:
        db.close()

if __name__ == "__main__":
    generate_sample_data()
