import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("No DATABASE_URL found in environment variables")
# For production environments like Render, database connections must use SSL.
# Supabase requires `sslmode=require`. This ensures it's appended if not present.
# This is a safe operation; if sslmode is already set, it won't be added again.
if "sslmode" not in DATABASE_URL:
    # Use '?' if no query params exist, otherwise use '&'
    separator = "?" if "?" not in DATABASE_URL else "&"
    DATABASE_URL += f"{separator}sslmode=require"
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
