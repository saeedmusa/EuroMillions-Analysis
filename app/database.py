from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL from environment or default to SQLite
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./euro_millions.db"
)

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create session factory
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize the database with all models."""
    from app.models.base import Base
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")
