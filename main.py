from fastapi import FastAPI, Depends, APIRouter, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
import supabase
from . import models, schemas, auth, crud
from .database import SessionLocal, engine, get_db
from supabase import create_client
from typing import List
import uuid

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Speech Improvement App API",
    description="Backend for handling prompts, audio processing, and transcriptions.",
    version="0.1.0",
)


#---Audio Configuration and Helpers---

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
SUPPORTED_MIME_TYPES = ["audio/mp3", "audio/wav", "audio/mpeg", "audio/webm", "audio/x-m4a"]
SUPABASE_BUCKET = "Recordings"


async def _validate_and_upload_audio(
    current_user: models.User,
    file: UploadFile,
) -> str:
    """
    Validates file type and size, then uploads to Supabase storage.
    Returns the storage path of the uploaded file.
    """
    if file.content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    file_contents = await file.read()
    if len(file_contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File Size exceeds the 10MB limit.")

    try:
        # Generate a unique path and filename.
        file_extension = ".tmp"
        if file.filename:
            # Basic extension extraction
            name_parts = file.filename.split('.')
            if len(name_parts) > 1:
                file_extension = f".{name_parts[-1]}"

        file_path = f"{current_user.id}/{uuid.uuid4()}{file_extension}"

        # Upload the file
        auth.supabase.storage.from_(SUPABASE_BUCKET).upload(
            file=file_contents,
            path=file_path,
            file_options={"content-type": file.content_type}
        )
        return file_path
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to storage: {str(e)}"
        )

def _get_signed_url_for_recording(recording: models.Recording) -> models.Recording:
    """
    Takes a recording object and populates the audio_url with a temporary signed URL.
    """
    try:
        signed_url_response = auth.supabase.storage.from_(
            SUPABASE_BUCKET
        ).create_signed_url(path=recording.audio_url, expires_in=60)
        # Overwrite the path with the temporary URL for the response object
        recording.audio_url = signed_url_response["signedURL"]
    except Exception:
        # This is not a critical failure. The recording is still created,
        # but we can't return a playable URL. The client can fetch it again.
        pass
    return recording


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

@app.get("/user/recording/{recording_id}", response_model=schemas.Recording)
def get_user_recording(
    recording_id: uuid.UUID,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve a specific recording for the authenticated user, including a
    temporary signed URL to access the audio file.
    """
    # 1. Fetch the recording from the database, ensuring it belongs to the user
    recording = crud.get_recording(
        db=db, recording_id=recording_id, user_id=current_user.id
    )

    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recording with id {recording_id} not found.",
        )

    # 2. Generate a signed URL for the private audio file and return
    return _get_signed_url_for_recording(recording)


@app.post("/user/prompt-and-recording", response_model=schemas.Recording, status_code=status.HTTP_201_CREATED)
async def create_prompt_and_recording(
    # Prompt fields sent as form data
    prompt_text: str = Form(...),
    # prompt_type_id is no longer accepted from the client.
    # Recording fields sent as form data
    duration_seconds: int = Form(...),
    file: UploadFile = File(...),
    # Dependencies
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new custom prompt and a corresponding recording in a single request.
    The prompt type is automatically set to 'Custom'.
    """
    # 1. --- Create the Prompt ---
    # The backend is now responsible for assigning the prompt type.
    # We will always use a "Custom" type for user-created prompts.
    prompt_type = crud.get_or_create_prompt_type(db, "Custom")

    prompt_schema = schemas.PromptCreate(text=prompt_text)
    new_prompt = crud.create_user_prompt(
        db=db,
        prompt=prompt_schema,
        user_id=current_user.id,
        prompt_type_id=prompt_type.id,
    )

    # 2. --- Validate and Upload Recording File ---
    file_path = await _validate_and_upload_audio(current_user, file)

    # 3. --- Create Recording DB Entry ---
    # Use the ID from the prompt we just created
    recording = crud.create_recording(
        db=db,
        user_id=current_user.id,
        prompt_id=new_prompt.id,
        duration=duration_seconds,
        audio_url=file_path
    )

    # 4. --- Generate Signed URL for immediate use ---
    return _get_signed_url_for_recording(recording)