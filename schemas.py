import uuid
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime

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
    type_id: int | None = None


class Prompt(BaseModel):
    id: int
    text: str
    user_id: uuid.UUID | None = None
    created_at: datetime
    prompt_type: PromptType | None = None

    model_config = ConfigDict(from_attributes=True)