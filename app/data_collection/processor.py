from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..models.base import Draw
from ..database import SessionLocal
from datetime import datetime, date

logger = logging.getLogger(__name__)

class DataProcessor:
    """Process and store lottery draw data."""
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db or SessionLocal()
    
    def process_draws(self, draws: List[Dict]) -> int:
        """Process a list of draw data and store in the database.
        
        Args:
            draws: List of draw dictionaries
            
        Returns:
            int: Number of new draws added to the database
        """
        if not draws:
            return 0
            
        new_draws = 0
        for draw_data in draws:
            if self._process_single_draw(draw_data):
                new_draws += 1
        
        try:
            self.db.commit()
            logger.info(f"Successfully processed {new_draws} new draws")
            return new_draws
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error committing to database: {e}")
            raise
    
    def _process_single_draw(self, draw_data: Dict) -> bool:
        """Process a single draw and add to database if it doesn't exist.
        
        Args:
            draw_data: Dictionary containing draw information
            
        Returns:
            bool: True if a new draw was added, False otherwise
        """
        try:
            # Check if draw already exists
            existing_draw = self.db.query(Draw).filter_by(draw_number=draw_data['draw_number']).first()
            if existing_draw:
                return False
                
            # Create new draw
            draw = Draw(
                draw_number=draw_data['draw_number'],
                draw_date=draw_data['draw_date'],
                ball1=draw_data['ball1'],
                ball2=draw_data['ball2'],
                ball3=draw_data['ball3'],
                ball4=draw_data['ball4'],
                ball5=draw_data['ball5'],
                lucky_star1=draw_data['lucky_star1'],
                lucky_star2=draw_data['lucky_star2'],
                jackpot=draw_data.get('jackpot')
            )
            
            self.db.add(draw)
            return True
            
        except Exception as e:
            logger.error(f"Error processing draw {draw_data.get('draw_number')}: {e}")
            self.db.rollback()
            return False
    
    def get_latest_draw_number(self) -> int:
        """Get the latest draw number from the database."""
        latest_draw = self.db.query(Draw).order_by(Draw.draw_number.desc()).first()
        return latest_draw.draw_number if latest_draw else 0
    
    def get_draws_since(self, draw_number: int) -> List[Draw]:
        """Get all draws since the specified draw number."""
        return self.db.query(Draw).filter(Draw.draw_number > draw_number).all()
    
    def close(self):
        """Close the database session."""
        if hasattr(self, 'db') and self.db:
            self.db.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
