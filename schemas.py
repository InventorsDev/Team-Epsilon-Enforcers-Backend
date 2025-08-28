import uuid
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from .models import RecordingStatus

# Base model for a user, this is what the API will return
class User(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str | None = None

    model_config = ConfigDict(from_attributes=True)

# ---PromptType Schemas---

class PromptTypeBase(BaseModel):
    label: str

class PromptType(PromptTypeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

# ---Prompt Schemas---
class PromptCreate(BaseModel):
    text: str
    # type_id is no longer part of the creation schema.
    # The backend will assign a "Custom" type automatically.


class Prompt(BaseModel):
    id: int
    text: str
    user_id: uuid.UUID | None = None
    created_at: datetime
    prompt_type: PromptType | None = None

    model_config = ConfigDict(from_attributes=True)


#---Recording Schemas---
class RecordingBase(BaseModel):
    prompt_id: int
    duration_seconds: int

class Recording(RecordingBase):
    id: uuid.UUID
    user_id: uuid.UUID
    audio_url: str
    transcript: str | None = None
    status: RecordingStatus
    created_at: datetime
    prompt: Prompt

    model_config = ConfigDict(from_attributes=True)