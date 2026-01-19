"""
Database configuration and connection management.
Handles PostgreSQL connection using SQLAlchemy.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    app_name: str = "Tulip Tea Backend API"
    app_version: str = "1.0.0"
    debug: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file (like Supabase keys)


settings = Settings()

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.debug  # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    Yields a database session and ensures it's closed after use.
    
    Handles database connection errors gracefully.
    Note: Database connection errors will be caught by the global exception handler
    which ensures CORS headers are sent.
    """
    db = None
    try:
        db = SessionLocal()
        # Test connection immediately to catch errors early
        db.execute(text("SELECT 1"))
    except Exception as e:
        # Close any partial session
        if db:
            try:
                db.close()
            except:
                pass
        
        # Log the error
        print(f"❌ [DB] Database connection error in get_db: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Re-raise - will be caught by global exception handler
        raise
    
    try:
        yield db
    finally:
        if db:
            db.close()

