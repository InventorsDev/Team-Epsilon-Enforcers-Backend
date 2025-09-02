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



# ---Analysis Schemas for the new synchronous endpoint---

class FillerWordsDetails(BaseModel):
    count: int
    ratio: float # e.g., 0.05 for 5%

class Scores(BaseModel):
    fluency: int
    pronunciation: int
    # Changed to an integer score for consistency
    filler_words: int
    pacing: int 

class Details(BaseModel):
    wer: float # Word Error Rate
    wpm: int # Words Per Minute
    pauses: int # Number of significant pauses
    confidence: float | None = None
    # Added details for filler words
    filler_words_details: FillerWordsDetails

class AnalysisResponse(BaseModel):
    transcript: str
    scores: Scores
    details: Details
    duration_seconds: float

class CombinedAnalysisResponse(AnalysisResponse):
    """The response model for the unified analysis and submission endpoint."""
    recording_id: uuid.UUID
    signed_audio_url: str