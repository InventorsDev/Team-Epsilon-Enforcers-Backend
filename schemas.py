import uuid
from pydantic import BaseModel, EmailStr, ConfigDict

# Base model for a user, this is what the API will return
class User(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str | None = None

    model_config = ConfigDict(from_attributes=True)
