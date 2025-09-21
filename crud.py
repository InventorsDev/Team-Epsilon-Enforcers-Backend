import uuid
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc
from typing import List
import models, schemas


def update_user(db: Session, user: models.User, user_update: schemas.UserUpdate) -> models.User:
    """Updates a user's attributes in the database."""
    # Get the update data, excluding any fields that were not set in the request
    update_data = user_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        if hasattr(user, key):
            setattr(user, key, value)
            
    db.add(user)
    db.commit()
    db.refresh(user)
    return user



def delete_user(db: Session, user_id: str):
    """
    Deletes a user and their associated data from the database.
    NOTE: This assumes that the database schema is set up with cascading deletes
    for related tables like prompts and recordings. If not, you must manually
    delete those records here before deleting the user.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()


def create_user_prompt(db: Session, prompt: schemas.PromptCreate, user_id: uuid.UUID, prompt_type_id: int):
    """
    Creates a new prompt and associates it with a user and a prompt type.
    """
    db_prompt = models.Prompt(
        text=prompt.text,
        prompt_type_id=prompt_type_id,
        user_id=user_id
    )
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    return db_prompt

# ---PromptType Functions---

def get_or_create_prompt_type(db: Session, label: str) -> models.PromptType:
    """
    Retrieves a prompt type by label, creating it if it doesn't exist.
    """
    prompt_type = db.query(models.PromptType).filter(models.PromptType.label == label).first()
    if not prompt_type:
        prompt_type = models.PromptType(label=label)
        db.add(prompt_type)
        db.commit()
        db.refresh(prompt_type)
    return prompt_type



#---Recording Functions---#
def create_recording(db: Session, user_id: uuid.UUID, prompt_id: int, duration: int, audio_url: str):
    """
    Creates a new recording entry in the database.
    """
    db_recording = models.Recording(
        user_id=user_id,
        prompt_id=prompt_id,
        duration_seconds = duration,
        audio_url=audio_url,
        status=models.RecordingStatus.PENDING # Default Status
    )
    db.add(db_recording)
    db.commit()
    db.refresh(db_recording)
    return db_recording
