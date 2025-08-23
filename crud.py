import uuid
from sqlalchemy.orm import Session
from sqlalchemy import or_
from . import models, schemas

# ---Prompt Functions---

def get_prompts_by_user(db: Session, user_id: uuid.UUID):
    """
    Retrieves all prompts available to a specific user.
    This includes both default prompts (user_id is Null) and 
    the user's own custom prompts
    """

    return db.query(models.Prompt).filter(or_(models.Prompt.user_id == user_id, models.Prompt.user_id == None)).all()

def create_user_prompt(db: Session, prompt: schemas.PromptCreate, user_id: uuid.UUID):
    """
    Creates a new prompt and associates it with a user
    """
    db_prompt = models.Prompt(
        text=prompt.text,
        prompt_type_id=prompt.type_id,
        user_id=user_id
    )
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    return db_prompt

# ---PromptType Functions---

def get_prompt_types(db: Session):
    """
    Retrieves all available prompt types.
    """
    return db.query(models.PromptType).all()