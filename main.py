from fastapi import FastAPI, Depends, APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import supabase
from . import models, schemas, auth, crud
from .database import SessionLocal, engine, get_db
from supabase import create_client
from typing import List

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

@app.get("/user/prompt", response_model=List[schemas.Prompt])
def get_prompts_for_user(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve all prompts available to the authenticated user.
    This includes default prompts and prompts created by the user.
    """

    prompts = crud.get_prompts_by_user(db=db, user_id=current_user.id)
    return prompts

@app.post("/user/prompt/create", response_model=schemas.Prompt, status_code=status.HTTP_201_CREATED)
def create_prompt_for_user(
    prompt: schemas.PromptCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new custom prompt for the authenticated user.
    """
    # If a type_id is provided, check if it exists
    if prompt.type_id is not None:
        prompt_type = db.query(models.PromptType).filter(models.PromptType.id == prompt.type_id).first()
        if not prompt_type:
            raise HTTPException(status_code=400, detail=f"PromptType with id {prompt.type_id} not found.")

    return crud.create_user_prompt(db=db, prompt=prompt, user_id=current_user.id)

@app.get("/prompt_types", response_model=List[schemas.PromptType])
def get_prompt_types(db: Session = Depends(get_db)):
    """
    Retrieve all available prompt types (e.g, Keynote, Debate)
    This is a public endpoint and does not require authentication
    """

    prompt_types = crud.get_prompt_types(db=db)
    return prompt_types