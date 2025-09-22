from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Body, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import supabase
import models, schemas, auth, crud
from database import  get_db
from supabase import AuthApiError, create_client
import os
from typing import List
import mimetypes
import uuid
from transcription_service import transcribe_audio_assemblyai_async
from analysis_service import perform_full_analysis_async
import logging

# models.Base.metadata.create_all(bind=engine) # This is removed for production. Use Alembic for migrations.

app = FastAPI(
    title="Speech Improvement App API",
    description="Backend for handling prompts, audio processing, and transcriptions.",
    version="0.1.0",
)

# --- CORS Middleware ---
# It's a security best practice to explicitly list your frontend's origins
# instead of using a wildcard ("*"), especially when allow_credentials=True.
# We'll read this from an environment variable.
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")

# The origins list will be a list of strings.
origins = [origin.strip() for origin in ALLOWED_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


#---Audio Configuration and Helpers---

MAX_FILE_SIZE = 50 * 1024 * 1024  # 10 MB
SUPPORTED_MIME_TYPES = ["audio/mp3", "audio/wav", "audio/mpeg", "audio/webm", "audio/x-m4a"]
SUPABASE_BUCKET = "Recordings"

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



@app.get("/")
def root():
    """
    Root endpoint providing a welcome message and a link to the API documentation.
    """
    return {"message": "Welcome to your speech coach in the cloud. Let's help you speak fluently, clearly, and with impact. Explore /docs for the API"}



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

@app.patch("/users/me", response_model=schemas.User)
def update_user_details(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the current user's details, such as their name.
    """
    return crud.update_user(db=db, user=current_user, user_update=user_update)


@app.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_account(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete the current user's account and all associated data.

    This is a destructive operation that will:
    1. Delete all of the user's recordings from cloud storage.
    2. Delete the user, their prompts, and recordings from the database.
    3. Delete the user from the Supabase authentication system.
    """
    user_id = current_user.id
    logger = logging.getLogger("uvicorn.error")
    
    # 1. Delete user from Supabase Auth first. This is the most critical step.
    # If this fails, we should not proceed with deleting their data in our system.
    try:
        # This requires the Supabase client to be initialized with the service_role key
        auth.supabase.auth.admin.delete_user(user_id)
        logger.info(f"Successfully deleted user {user_id} from Supabase Auth.")
    except AuthApiError as e:
        # If the user is not found, they might have been deleted already.
        # We can proceed if our goal is to ensure the user is gone.
        if "User not found" in str(e):
             logger.warning(f"User {user_id} not found in Supabase Auth. Proceeding with DB cleanup.")
        else:
            logger.error(f"Critical error: Failed to delete user {user_id} from Supabase Auth: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete user from authentication service.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while trying to delete user {user_id} from Supabase Auth: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during account deletion.")

    # 2. Delete all files from Supabase Storage
    try:
        files_to_delete = auth.supabase.storage.from_(SUPABASE_BUCKET).list(path=str(user_id))
        if files_to_delete:
            file_paths = [f"{user_id}/{file['name']}" for file in files_to_delete]
            auth.supabase.storage.from_(SUPABASE_BUCKET).remove(file_paths)
            logger.info(f"Successfully deleted {len(file_paths)} files from storage for user {user_id}.")
    except Exception as e:
        logger.error(f"Error deleting files from storage for user {user_id}: {e}", exc_info=True)
        # This is a non-critical failure. The user is deleted, but files are orphaned.
        # A separate cleanup job could handle these.

    # 3. Delete user and associated data from the database
    crud.delete_user(db=db, user_id=user_id)
    logger.info(f"Successfully deleted user {user_id} from the database.")


# NEW: Prompt and Audio Management

@app.post("/recordings/submit-and-analyze", response_model=schemas.CombinedAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def submit_and_analyze(
    prompt_text: str = Form(...),
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """A unified endpoint to submit an audio recording against a prompt for analysis.

    This endpoint performs the following actions:
    1.  Validates the uploaded audio file.
    2.  Sends the audio for transcription and analysis.
    3.  Creates a new custom prompt and its associated recording in the database.
    4.  Uploads the audio file to cloud storage.
    5.  Returns the full analysis results, the new recording's ID, and a temporary signed URL for playback.
    """
    # Logger configuration
    logger = logging.getLogger("uvicorn.error")  # Get the default logger used by FastAPI/Uvicorn
    logger.setLevel(logging.INFO)  # Log INFO level and above

    # 1. --- File Validation ---
    if file.content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    file_contents = await file.read()
    if len(file_contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds the 50MB limit.")

    # 2. --- Transcription and Analysis ---
    # We run this first as it is often the longest part of the process.
    try:
        # Add logging
        # logger.info(f"Received audio file: {file.filename}, type: {file.content_type}")
        # logger.info(f"Prompt text: {prompt_text}")
        
        transcript, word_timestamps, confidence = await transcribe_audio_assemblyai_async(file_contents, file.content_type)
        # logger.info(f"Transcription result: {transcript[:100]}...")  # Log first 100 chars
        # logger.info(f"Word_Timestamps: {word_timestamps}")
        
        if transcript is None:
            raise HTTPException(status_code=502, detail="Failed to transcribe audio via external service.")
        
        analysis_results = await perform_full_analysis_async(prompt_text, transcript, word_timestamps, confidence)
        logger.info(f"Analysis completed successfully: {analysis_results}")
        
    except Exception as e:
        logger.error(f"Error in submit_and_analyze: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

    # 3. --- Database and Storage Operations ---
    # A. Create the Prompt
    prompt_type = crud.get_or_create_prompt_type(db, "Custom")
    prompt_schema = schemas.PromptCreate(text=prompt_text)
    new_prompt = crud.create_user_prompt(
        db=db,
        prompt=prompt_schema,
        user_id=current_user.id,
        prompt_type_id=prompt_type.id
    )

    # B. Upload to Supabase Storage
    file_extension = mimetypes.guess_extension(file.content_type) or ".tmp"
    file_path = f"{current_user.id}/{uuid.uuid4()}{file_extension}"
    try:
        auth.supabase.storage.from_(SUPABASE_BUCKET).upload(
            file=file_contents,
            path=file_path,
            file_options={"content-type": file.content_type}
        )
    except Exception as e:
        # If analysis succeeded but upload fails, we can't save the recording.
        # We could still return the analysis, but it's better to signal a server error.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to storage: {str(e)}"
        )

    # C. Create Recording DB Entry
    recording = crud.create_recording(
        db=db,
        user_id=current_user.id,
        prompt_id=new_prompt.id,
        duration=int(analysis_results["duration_seconds"]),
        audio_url=file_path
    )

    # NEW: Update status to DONE to reflect completion
    recording.status = models.RecordingStatus.DONE
    db.add(recording)
    db.commit()
    db.refresh(recording)

    # 4. --- Generate Signed URL ---
    # This function modifies the recording object in-place for the response
    recording_with_url = _get_signed_url_for_recording(recording)

    # 5. --- Combine and Return Response ---
    # Unpack the analysis results and add the recording-specific info.
    return {
        "recording_id": recording.id,
        "signed_audio_url": recording_with_url.audio_url,
        **analysis_results,
    }
