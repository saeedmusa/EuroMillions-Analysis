import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Database configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./euro_millions.db')
    
    # API Configuration
    LOTTERY_API_BASE_URL = 'https://api.lotteryresultsapi.com'
    LOTTERY_API_TOKEN = os.getenv('LOTTERY_API_TOKEN', '')
    
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Application settings
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
