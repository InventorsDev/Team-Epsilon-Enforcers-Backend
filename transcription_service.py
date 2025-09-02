# /assemblyai_service.py

import os
import asyncio
import mimetypes
import logging
import tempfile
from fastapi.concurrency import run_in_threadpool
import assemblyai as aai  # AssemblyAI SDK

# --- Configuration ---
POLLING_INTERVAL_SECONDS = 5
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- AssemblyAI Client Initialization ---
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

if not ASSEMBLYAI_API_KEY:
    raise ValueError("ASSEMBLYAI_API_KEY environment variable not set.")

aai.settings.api_key = ASSEMBLYAI_API_KEY
client = aai.Transcriber()

async def transcribe_audio_assemblyai_async(audio_bytes: bytes, content_type: str):
    """
    Transcribes audio using the AssemblyAI API by submitting an in-memory file.
    This function submits a job, polls for its completion, and then returns
    the transcript text and word-level timestamps.

    Args:
        audio_bytes: The raw bytes of the audio file.
        content_type: The MIME type of the audio file (e.g., "audio/wav").
    """
    try:
        extension = mimetypes.guess_extension(content_type) or ".tmp"

        # 1. --- Write in-memory bytes to a temporary file for upload ---
        with tempfile.NamedTemporaryFile(suffix=extension, delete=True) as temp_audio_file:
            temp_audio_file.write(audio_bytes)
            temp_audio_file.flush()

            # 2. --- Submit job to AssemblyAI ---
            config = aai.TranscriptionConfig(speaker_labels=True)
            transcript = await run_in_threadpool(
                client.transcribe, temp_audio_file.name, config
            )

        if transcript.status == aai.TranscriptStatus.error:
            logger.error(f"AssemblyAI job failed: {transcript.error}")
            return None, None, None

        if not transcript.text or not transcript.words:
            logger.warning("AssemblyAI job succeeded but produced no text or words.")
            return None, None, None

        # 3. --- Extract text and word-level timestamps ---
        transcript_text = transcript.text
        overall_confidence = transcript.confidence
        word_timestamps = [
            {
                "word": w.text,
                "start": w.start / 1000,  # in seconds
                "end": w.end / 1000,      # in seconds
            }
            for w in transcript.words
        ]

        if not word_timestamps:
            logger.warning("AssemblyAI job produced transcript but no word timestamps.")
            return None, None, None

        return transcript_text, word_timestamps, overall_confidence

    except Exception as e:
        logger.error(f"An unexpected error occurred with AssemblyAI service: {e}", exc_info=True)
        return None, None, None
