import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from .models import Base

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Handle Railway's postgres:// URL format
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fallback for local development
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./users.db"
    print("WARNING: No DATABASE_URL found, using SQLite for development")

# Create engine
if "postgresql" in DATABASE_URL:
    # PostgreSQL settings
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )
else:
    # SQLite settings (for local dev)
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

@contextmanager
def get_db():
    """Database session context manager"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_db_session() -> Session:
    """Get database session for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
