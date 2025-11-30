from sqlmodel import Session
from database import engine


def get_session():
    # FastAPI dependency (for Depends)
    with Session(engine) as session:
        yield session


def get_session_sync():
    # For scripts like seed.py
    return Session(engine)
