from fastapi import FastAPI, Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import supabase
from . import models, schemas, auth
from .database import SessionLocal, engine, get_db
from supabase import create_client

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Speech Improvement App API",
    description="Backend for handling prompts, audio processing, and transcriptions.",
    version="0.1.0",
)


@app.get("/health-check")
def health_check(db: Session = Depends(get_db)):
    """
    Checks if the API can connect to the database.
    """
    try:
        # Try to execute a simple query
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database_connection": "successful"}
    except Exception as e:
        return {"status": "error", "database_connection": "failed", "detail": str(e)}
    
    
# NEW: Protected endpoint
@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: schemas.User = Depends(auth.get_current_user)):
    """
    Fetch the profile of the currently authenticated user.
    This endpoint is protected; a valid JWT is required.
    """

    return current_user