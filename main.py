from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from . import models
from .database import engine, get_db

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