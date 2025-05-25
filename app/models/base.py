from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Date, Numeric

Base = declarative_base()

class Draw(Base):
    """Model for storing EuroMillions draw information."""
    __tablename__ = 'draws'
    
    id = Column(Integer, primary_key=True, index=True)
    draw_number = Column(Integer, nullable=True, index=True)  # Made nullable since API doesn't always provide it
    draw_date = Column(Date, nullable=False, unique=True, index=True)  # Made unique since each date should have only one draw
    ball1 = Column(Integer, nullable=False)
    ball2 = Column(Integer, nullable=False)
    ball3 = Column(Integer, nullable=False)
    ball4 = Column(Integer, nullable=False)
    ball5 = Column(Integer, nullable=False)
    lucky_star1 = Column(Integer, nullable=False)
    lucky_star2 = Column(Integer, nullable=False)
    jackpot = Column(Numeric(15, 2), nullable=True)
    
    def __repr__(self):
        return f"<Draw(draw_number={self.draw_number}, date={self.draw_date})>"
