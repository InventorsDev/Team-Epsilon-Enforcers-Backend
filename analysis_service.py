# /analysis_service.py

import logging
import re
import statistics
from typing import List, Dict, Optional

import jiwer
from fastapi.concurrency import run_in_threadpool



# --- Logger Configuration ---
logger = logging.getLogger(__name__)

# --- Constants for Scoring ---
# WPM scoring: 100 score for 140-160 WPM. Score degrades over a tolerance of 35 WPM outside this range.
IDEAL_WPM_MIN = 140
IDEAL_WPM_MAX = 160
WPM_TOLERANCE = 35
PAUSE_THRESHOLD_MS = 1000  # A pause is considered significant if it's longer than 1000ms
FILLER_WORDS = {
    'um', 'uh', 'er', 'ah', 'like', 'you know', 'so', 'right', 'okay', 'i mean'
}
FILLER_WORD_RATIO_THRESHOLD = 0.05  # Ratio of filler words for a score of 0

# Pacing analysis constants
PACING_MIN_DURATION_S = 10      # Min duration in seconds to attempt pacing analysis
PACING_MIN_CHUNKS = 2           # Min number of chunks for a full pacing analysis
PACING_CHUNK_DURATION_S = 10    # Duration of each chunk in seconds
PACING_STD_DEV_TOLERANCE = 35   # WPM standard deviation for a score of 0. A higher value is more forgiving.



# --- Helper Functions ---

def normalize_score(value, ideal, range_width):
    """Normalizes a value to a 0-100 score based on its distance from an ideal value."""
    diff = abs(value - ideal)
    score = 100 * max(0, 1 - (diff / range_width))
    return int(score)



def normalize_score_with_plateau(value, ideal_min, ideal_max, tolerance):
    """
    Normalizes a value to a 0-100 score, with a plateau for an ideal range.
    Score is 100 within [ideal_min, ideal_max].
    Score decreases linearly to 0 over the tolerance width outside this range.
    """
    if ideal_min <= value <= ideal_max:
        return 100
    elif value < ideal_min:
        diff = ideal_min - value
    else:  # value > ideal_max
        diff = value - ideal_max
    
    score = 100 * max(0, 1 - (diff / tolerance))
    return int(score)



def normalize_inverted_score(value, bad_threshold):
    """Normalizes a value where lower is better (like WER or filler ratio) to a 0-100 score."""
    # Score is 100 if value is 0, and 0 if value is at or above bad_threshold.
    score = 100 * max(0, 1 - (value / bad_threshold))
    return int(score)



# --- Core Analysis Functions ---

def analyze_fluency(word_timestamps: List[Dict], duration_seconds: float):
    """
    Calculates Words Per Minute (WPM), a fluency score based on WPM,
    and the number of significant pauses.

    Returns:
        A tuple of (wpm, pause_count, fluency_score).
    """
    # Use the length of word_timestamps for a more accurate word count
    num_words = len(word_timestamps)
    if duration_seconds == 0 or num_words == 0:
        return 0, 0, 0
    
    # Calculate WPM
    wpm = int((num_words / duration_seconds) * 60)
    fluency_score = normalize_score_with_plateau(wpm, IDEAL_WPM_MIN, IDEAL_WPM_MAX, WPM_TOLERANCE)
    
    # Count pauses
    pause_count = 0
    # Iterate through pairs of words to find the gap between them
    if len(word_timestamps) > 1:
        for current_word, next_word in zip(word_timestamps, word_timestamps[1:]):
            pause_duration_ms = (next_word['start'] - current_word['end']) * 1000
            if pause_duration_ms > PAUSE_THRESHOLD_MS:
                pause_count += 1
                
    return wpm, pause_count, fluency_score

def analyze_pronunciation(prompt: str, transcript: str) -> tuple[float, int]:
    """
    Analyzes pronunciation accuracy using Word Error Rate (WER)
    and converts it to a 0-100 score.
    """
    try:
        # Calculate WER. jiwer's default transformation handles normalization
        # (lowercase, punctuation removal, etc.), which is suitable for this use case.
        wer = jiwer.wer(
            reference=prompt,
            hypothesis=transcript,
        )

        # Convert WER to a 0-100 score where 0 WER = 100 score
        pronunciation_score = int(max(0, 100 * (1 - wer)))
        
        return wer, pronunciation_score
    except Exception as e:
        logger.error(f"Error calculating pronunciation score: {str(e)}")
        return 1.0, 0  # Return worst case scores on error

def analyze_filler_words(transcript: str, total_words: int):
    """
    Counts filler words, calculates their ratio, and generates a score.

    Returns:
        A tuple of (count, ratio, score, list_of_fillers).
    """
    # Use regex to find whole words only
    found_fillers = re.findall(r'\b(' + '|'.join(FILLER_WORDS) + r')\b', transcript.lower())
    count = len(found_fillers)
    
    ratio = count / total_words if total_words > 0 else 0
    
    # Convert ratio to a 0-100 score.
    # A ratio of 5% (0.05) or higher results in a score of 0.
    score = normalize_inverted_score(ratio, FILLER_WORD_RATIO_THRESHOLD)
    
    return count, round(ratio, 4), score, found_fillers

def analyze_pacing(word_timestamps: List[Dict], duration_seconds: float):
    """
    Analyzes the consistency of the speaking pace and returns a score.

    Returns:
        An integer pacing score from 0-100.
    """
    if duration_seconds < PACING_MIN_DURATION_S or not word_timestamps:
        return 100  # Not enough data for a meaningful pacing score

    num_chunks = int(duration_seconds / PACING_CHUNK_DURATION_S)
    if num_chunks < PACING_MIN_CHUNKS:
        return 90  # Still not enough data for full analysis, assume good pacing

    words_per_chunk = [0] * num_chunks
    for word in word_timestamps:
        chunk_index = int(word['start'] // PACING_CHUNK_DURATION_S)
        if chunk_index < num_chunks:
            words_per_chunk[chunk_index] += 1
            
    wpm_per_chunk = [(count / PACING_CHUNK_DURATION_S) * 60 for count in words_per_chunk]

    # If no words were spoken in the analyzed chunks, pacing score is 0.
    if not any(wpm_per_chunk):
        return 0

    # Calculate the population standard deviation of WPM across chunks.
    # A lower std_dev indicates more consistent pacing.
    std_dev = statistics.pstdev(wpm_per_chunk)
    
    # Normalize the standard deviation to a 0-100 score. A lower std_dev is better.
    # A std_dev of PACING_STD_DEV_TOLERANCE WPM or more is considered highly
    # inconsistent and results in a score of 0.
    pacing_score = normalize_score(std_dev, 0, PACING_STD_DEV_TOLERANCE)

    return pacing_score

def perform_full_analysis(prompt: str, transcript: str, word_timestamps: List[Dict], confidence: Optional[float]):
    """Orchestrator function to run all analyses and format the output."""
    # Determine the duration of spoken content and the number of words.
    # The duration is based on the end time of the last word, which is more
    # accurate for WPM calculations than using the full audio file duration.
    if not word_timestamps:
        duration = 0
        num_words = 0
    else:
        duration = word_timestamps[-1]['end']
        num_words = len(word_timestamps)

    # If no words were detected, return a zero-score analysis as no meaningful
    # evaluation can be performed.
    if num_words == 0:
        wer, _ = analyze_pronunciation(prompt, transcript) # Still calculate WER for info
        return {
            "duration_seconds": round(duration, 2),
            "transcript": transcript,
            "scores": {
                "fluency": 0,
                "pronunciation": 0,
                "filler_words": 0,
                "pacing": 0,
            },
            "details": {
                "wer": round(wer, 4),
                "wpm": 0,
                "pauses": 0,
                "filler_words_details": {"count": 0, "ratio": 0, "words": []},
                "confidence": confidence,
            }
        }

    wpm, pauses, fluency_score = analyze_fluency(word_timestamps, duration)
    wer, pronunciation_score = analyze_pronunciation(prompt, transcript)
    filler_count, filler_ratio, filler_score, found_fillers = analyze_filler_words(transcript, num_words)
    pacing_score = analyze_pacing(word_timestamps, duration)

    return {
        "duration_seconds": round(duration, 2),
        "transcript": transcript,
        "scores": {
            "fluency": fluency_score,
            "pronunciation": pronunciation_score,
            # The filler_words score is now a single integer for consistency,
            # while the details are in the 'details' section.
            "filler_words": filler_score,
            "pacing": pacing_score,
        },
        "details": {
            "wer": round(wer, 4),
            "wpm": wpm,
            "pauses": pauses,
            "filler_words_details": {
                "count": filler_count,
                "ratio": filler_ratio,
                "words": found_fillers
            },
            "confidence": confidence,
        }
    }

async def perform_full_analysis_async(prompt: str, transcript: str, word_timestamps: List[Dict], confidence: Optional[float]):
    """
    Asynchronous wrapper for perform_full_analysis.
    Runs the synchronous, potentially CPU-bound analysis in a thread pool.
    """
    return await run_in_threadpool(
        perform_full_analysis,
        prompt=prompt,
        transcript=transcript,
        word_timestamps=word_timestamps,
        confidence=confidence
    )