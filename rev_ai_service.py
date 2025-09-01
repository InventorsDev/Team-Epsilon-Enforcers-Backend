# /revai_service.py

import os
import asyncio
import mimetypes
import logging
import uuid
from rev_ai.models import JobStatus
from rev_ai.apiclient import RevAiAPIClient
import io
import tempfile
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
    Transcribes audio using the Rev.ai API by submitting an in-memory file.
    This function submits a job, polls for its completion, and then returns
    the transcript and timestamps. This is an async version that uses a
    thread pool for blocking SDK calls.

    Args:
        audio_bytes: The raw bytes of the audio file.
        content_type: The MIME type of the audio file (e.g., "audio/wav").
    """
    try:
        extension = mimetypes.guess_extension(content_type) or ".tmp"

        # 1. --- Submit the transcription job ---
        # The Rev.ai SDK's `submit_job_local_file` expects a file path.
        # To use our in-memory audio_bytes, we write them to a temporary file.
        with tempfile.NamedTemporaryFile(suffix=extension, delete=True) as temp_audio_file:
            temp_audio_file.write(audio_bytes)
            temp_audio_file.flush()  # Ensure data is written to disk

            # The SDK's submit_job_local_file is a blocking network call.
            # We run it in a thread pool to avoid blocking the event loop.
            job = await run_in_threadpool(
                client.submit_job_local_file,
                filename=temp_audio_file.name
            )
            if not job:
                logger.error("Failed to submit job to Rev.ai")
                return None, None

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
        # The to_text() method is a fast, local, synchronous operation that processes
        # the in-memory object. It doesn't require a thread pool.
        transcript = await run_in_threadpool(client.get_transcript_text, job.id)

        word_timestamps = []
        for monologue in transcript_object.monologues:
            for element in monologue.elements:
                if element.type_ == "word":
                    word_timestamps.append({
                        "word": element.value,
                        "start": element.ts,
                        "end": element.end_ts
                    })

        return transcript, word_timestamps

    except Exception as e:
        logger.error(f"An unexpected error occurred with Rev.ai service: {e}", exc_info=True)
        return None, None