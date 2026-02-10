from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine
from app.core.config import settings

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    with Session(engine) as session:
        yield session
