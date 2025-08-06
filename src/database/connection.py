import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

# Database connection setup
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/smartclass')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

@contextmanager
def get_session():
    """Context manager for database sessions"""
    session = Session()
    try:
        yield session
    finally:
        session.close()