# /analysis_service.py

import logging
import jiwer
import re
from fastapi.concurrency import run_in_threadpool
from typing import List, Dict

# --- Logger Configuration ---
logger = logging.getLogger(__name__)

# --- Constants for Scoring ---
IDEAL_WPM = 150
WPM_RANGE = 30  # Points start to decrease outside of IDEAL_WPM +/- this range
PAUSE_THRESHOLD_MS = 500  # A pause is longer than 500ms
FILLER_WORDS = {
    'um', 'uh', 'er', 'ah', 'like', 'you know', 'so', 'right', 'okay', 'i mean'
}

# --- Helper Functions ---

def normalize_score(value, ideal, range_width):
    """Normalizes a value to a 0-100 score based on its distance from an ideal value."""
    diff = abs(value - ideal)
    score = 100 * max(0, 1 - (diff / range_width))
    return int(score)

def normalize_inverted_score(value, bad_threshold):
    """Normalizes a value where lower is better (like WER or filler ratio) to a 0-100 score."""
    # Score is 100 if value is 0, and 0 if value is at or above bad_threshold.
    score = 100 * max(0, 1 - (value / bad_threshold))
    return int(score)

# --- Core Analysis Functions ---

def analyze_fluency(transcript: str, word_timestamps: List[Dict], duration_seconds: float):
    """
    Calculates Words Per Minute (WPM), a fluency score based on WPM,
    and the number of significant pauses.

    Returns:
        A tuple of (wpm, pause_count, fluency_score).
    """
    num_words = len(transcript.split())
    if duration_seconds == 0:
        return 0, 0, 0
    
    # Calculate WPM
    wpm = int((num_words / duration_seconds) * 60)
    fluency_score = normalize_score(wpm, IDEAL_WPM, WPM_RANGE)
    
    # Count pauses
    pause_count = 0
    if len(word_timestamps) > 1:
        for i in range(len(word_timestamps) - 1):
            pause_duration = (word_timestamps[i+1]['start'] - word_timestamps[i]['end']) * 1000
            if pause_duration > PAUSE_THRESHOLD_MS:
                pause_count += 1
                
    return wpm, pause_count, fluency_score

def analyze_pronunciation(prompt: str, transcript: str) -> tuple[float, float]:
    """
    Analyzes pronunciation accuracy using Word Error Rate (WER)
    and converts it to a 0-100 score.
    """
    try:
        # Use jiwer's default transformations
        transformation = jiwer.Compose([
            jiwer.ToLowerCase(),
            jiwer.RemoveMultipleSpaces(),
            jiwer.Strip(),
            jiwer.RemovePunctuation(),
            jiwer.SentencesToListOfWords(),
        ])
        
        # Calculate WER using the transformation
        wer = jiwer.wer(
            reference=prompt,
            hypothesis=transcript,
            truth_transform=transformation,
            hypothesis_transform=transformation
        )
        
        # Convert WER to a 0-100 score where 0 WER = 100 score
        pronunciation_score = max(0, 100 * (1 - wer))
        
        return wer, pronunciation_score
    except Exception as e:
        logger.error(f"Error calculating pronunciation score: {str(e)}")
        return 1.0, 0.0  # Return worst case scores on error

def analyze_filler_words(transcript: str):
    """
    Counts filler words, calculates their ratio, and generates a score.

    Returns:
        A tuple of (count, ratio, score).
    """
    # Use regex to find whole words only
    found_fillers = re.findall(r'\b(' + '|'.join(FILLER_WORDS) + r')\b', transcript.lower())
    count = len(found_fillers)
    
    total_words = len(transcript.split())
    ratio = count / total_words if total_words > 0 else 0
    
    # Convert ratio to a 0-100 score.
    # A ratio of 5% (0.05) or higher results in a score of 0.
    score = normalize_inverted_score(ratio, 0.05)
    
    return count, round(ratio, 4), score

def analyze_pacing(word_timestamps: List[Dict], duration_seconds: float):
    """
    Analyzes the consistency of the speaking pace and returns a score.

    Returns:
        An integer pacing score from 0-100.
    """
    if duration_seconds < 10 or not word_timestamps:
        return 100 # Not enough data for a meaningful pacing score

    chunk_duration = 10  # Analyze in 10-second chunks
    num_chunks = int(duration_seconds / chunk_duration)
    if num_chunks < 2:
        return 90 # Still not enough data, assume good pacing

    words_per_chunk = [0] * num_chunks
    for word in word_timestamps:
        chunk_index = int(word['start'] // chunk_duration)
        if chunk_index < num_chunks:
            words_per_chunk[chunk_index] += 1
            
    wpm_per_chunk = [(count / chunk_duration) * 60 for count in words_per_chunk]

    # Calculate standard deviation of WPM
    mean_wpm = sum(wpm_per_chunk) / num_chunks
    if mean_wpm == 0:
        return 0
        
    variance = sum([(wpm - mean_wpm) ** 2 for wpm in wpm_per_chunk]) / num_chunks
    std_dev = variance ** 0.5
    
    # Normalize score. A lower std_dev is better.
    # A std_dev of 20 WPM could be a threshold for a decent score.
    pacing_score = normalize_score(std_dev, 0, 30)

    return pacing_score

def perform_full_analysis(prompt: str, transcript: str, word_timestamps: List[Dict]):
    """Orchestrator function to run all analyses and format the output."""
    if not word_timestamps:
        duration = 0
    else:
        duration = word_timestamps[-1]['end']

    wpm, pauses, fluency_score = analyze_fluency(transcript, word_timestamps, duration)
    wer, pronunciation_score = analyze_pronunciation(prompt, transcript)
    filler_count, filler_ratio, filler_score = analyze_filler_words(transcript)
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
            "filler_words_details": {"count": filler_count, "ratio": filler_ratio},
        }
    }

async def perform_full_analysis_async(prompt: str, transcript: str, word_timestamps: List[Dict]):
    """
    Asynchronous wrapper for perform_full_analysis.
    Runs the synchronous, potentially CPU-bound analysis in a thread pool.
    """
    return await run_in_threadpool(
        perform_full_analysis,
        prompt=prompt,
        transcript=transcript,
        word_timestamps=word_timestamps
    )