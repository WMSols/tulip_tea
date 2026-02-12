"""
Database configuration and connection management.
Handles PostgreSQL connection using SQLAlchemy.
"""
from sqlalchemy import create_engine
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
    # Frontend URL for CORS (production)
    frontend_url: str = ""
    # Supabase configuration (for frontend) - loaded from environment
    # These match the .env variable names (case-insensitive)
    supabase_url: str = ""
    supabase_anon_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file


settings = Settings()

# Create SQLAlchemy engine with optimized connection pooling
# Pool configuration optimized for concurrent requests:
# - pool_size: Base number of connections to maintain (20 = handles ~20 concurrent requests)
# - max_overflow: Additional connections allowed during peak (40 = up to 60 total connections)
# - pool_recycle: Recycle connections after 1 hour to prevent stale connections
# - pool_pre_ping: Verify connections are alive before using (prevents connection errors)
# - connect_args: Connection timeout and query timeout to prevent hanging
engine = create_engine(
    settings.database_url,
    pool_size=10,  # Base pool size - handles normal concurrent load
    max_overflow=10,  # Additional connections during peak (total max: 60 connections)
    pool_recycle=3600,  # Recycle connections after 1 hour (prevents stale connections)
    pool_pre_ping=True,  # Verify connections before using (prevents connection errors)
    connect_args={
        "connect_timeout": 10,  # 10 second connection timeout
        "options": "-c stastement_timeout=30000"  # 30 second query timeout (in milliseconds)
    },
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
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

