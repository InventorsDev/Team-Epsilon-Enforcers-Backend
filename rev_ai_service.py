# /revai_service.py

import os
import asyncio
import mimetypes
import logging
import tempfile
from rev_ai.models import JobStatus
from rev_ai.apiclient import RevAiAPIClient
import io
from fastapi.concurrency import run_in_threadpool

# --- Configuration ---
POLLING_INTERVAL_SECONDS = 5
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Rev.ai Client Initialization ---
REVAI_API_KEY = os.getenv("REVAI_API_KEY")

if not REVAI_API_KEY:
    raise ValueError("REVAI_API_KEY environment variable not set.")

# Initialize the client
client = RevAiAPIClient(REVAI_API_KEY)

async def transcribe_audio_revai_async(audio_bytes: bytes, content_type: str):
    """
    Transcribes audio using the Rev.ai API. This function submits a job,
    polls for its completion, and then returns the transcript and timestamps.
    This is an async version that uses a thread pool for blocking SDK calls.

    Args:
        audio_bytes: The raw bytes of the audio file.
        content_type: The MIME type of the audio file (e.g., "audio/wav").
    """
    temp_file_path = None
    try:
        # Determine a safe file extension from the content type, defaulting to .tmp
        extension = mimetypes.guess_extension(content_type) or ".tmp"

        # Create a temporary file to write the audio bytes to, so we can use submit_job_local_file.
        # The file is created with delete=False so we can get its path and clean it up manually.
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name

        # 1. --- Submit the transcription job ---
        # The SDK's submit_job_local_file is a blocking I/O call that reads from disk.
        job = await run_in_threadpool(
            client.submit_job_local_file, filename=temp_file_path
        )
        logger.info(f"Submitted Rev.ai job with ID: {job.id}")

        # 2. --- Poll for job completion ---
        while True:
            # get_job_details is a blocking network call.
            details = await run_in_threadpool(client.get_job_details, job.id)
            if details.status == JobStatus.TRANSCRIBED:
                logger.info(f"Job {job.id} has been transcribed.")
                break
            if details.status == JobStatus.FAILED:
                logger.error(f"Job {job.id} failed: {details.failure_detail}")
                return None, None

            # Use asyncio.sleep to wait without blocking the event loop.
            await asyncio.sleep(POLLING_INTERVAL_SECONDS)

        # 3. --- Fetch and process the transcript ---
        # get_transcript_object is a blocking network call.
        transcript_object = await run_in_threadpool(client.get_transcript_object, job.id)

        # 4. --- Format the output to match what analysis_service expects ---
        # to_text() is a local, synchronous operation, but we run it in the pool
        # for consistency and to be safe.
        full_transcript = await run_in_threadpool(transcript_object.to_text)

        word_timestamps = []
        for monologue in transcript_object.monologues:
            for element in monologue.elements:
                if element.type_ == "word":
                    word_timestamps.append({
                        "word": element.value,
                        "start": element.ts,
                        "end": element.end_ts
                    })

        return full_transcript, word_timestamps

    except Exception as e:
        logger.error(f"An unexpected error occurred with Rev.ai service: {e}", exc_info=True)
        return None, None
    finally:
        # Ensure the temporary file is cleaned up
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"Cleaned up temporary file: {temp_file_path}")