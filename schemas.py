from typing import Optional, List
import uuid
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime
from models import RecordingStatus

# Base model for a user, this is what the API will return
class User(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Schema for updating user details."""
    name: Optional[str] = None
    # Email is tied to the authentication provider and should not be updated here.

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
    count: int = Field(..., description="Total number of filler words detected.")
    ratio: float = Field(..., description="Ratio of filler words to total words (e.g., 0.05 for 5%).")
    words: List[str] = Field(..., description="A list of the filler words that were detected, in order of occurrence.")

class Scores(BaseModel):
    fluency: int = Field(..., description="Score from 0-100 based on the calculated Words Per Minute (WPM).")
    pronunciation: int = Field(..., description="Score from 0-100 based on the Word Error Rate (WER). 100 is a perfect match.")
    # Changed to an integer score for consistency
    filler_words: int = Field(..., description="Score from 0-100 based on the ratio of filler words. A higher score is better, with 100 indicating no filler words.")
    pacing: int = Field(..., description="Score from 0-100 based on the consistency of the speaking pace.")

class Details(BaseModel):
    wer: float = Field(..., description="Word Error Rate. Lower is better (0.0 is a perfect match).")
    wpm: int = Field(..., description="Calculated Words Per Minute.")
    pauses: int = Field(..., description="Number of significant pauses (longer than 1 second) detected.")
    confidence: float | None = Field(None, description="Overall confidence of the transcription from the speech-to-text service (0.0 to 1.0).")
    # Added details for filler words
    filler_words_details: FillerWordsDetails

class AnalysisResponse(BaseModel):
    transcript: str = Field(..., description="The transcribed text from the audio.")
    scores: Scores
    details: Details
    duration_seconds: float = Field(..., description="The duration of the spoken content in seconds.")

class CombinedAnalysisResponse(AnalysisResponse):
    """The response model for the unified analysis and submission endpoint."""
    recording_id: uuid.UUID
    signed_audio_url: str