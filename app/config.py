import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
AUDIO_INPUT_DIR = DATA_DIR / "audio_input"  
AUDIO_OUTPUT_DIR = DATA_DIR / "audio_output"
PRAAT_OUTPUT_DIR = DATA_DIR / "praat_output"
MODELS_DIR = DATA_DIR / "models"
PRAAT_TIMEOUT = 10
MAX_AUDIO_DURATION = 180
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Create directories if they don't exist
for dir_path in [AUDIO_INPUT_DIR, AUDIO_OUTPUT_DIR, PRAAT_OUTPUT_DIR, MODELS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Docker settings
PRAAT_CONTAINER_NAME = os.getenv("PRAAT_CONTAINER_NAME", "hskk-praat-scoring_praat_1")
PRAAT_IMAGE = "hskk-praat-scoring_praat"

# Audio settings
SUPPORTED_FORMATS = [".wav", ".mp3", ".m4a", ".flac"]
TARGET_SAMPLE_RATE = 16000

# HSKK Scoring thresholds

SCORING_WEIGHTS = {
    "pronunciation": 0.35,
    "fluency": 0.35,
    "grammar": 0.15,
    "vocabulary": 0.15
}

HSKK_THRESHOLDS = {
    "elementary": {
        "pitch_range_min": 50,
        "speech_rate_min": 60,
        "speech_rate_max": 300,
        "pause_ratio_max": 0.4,
        "hnr_min": 15,
        "pronunciation_accuracy_min": 0.6
    },
    "intermediate": {
        "pitch_range_min": 80,
        "speech_rate_min": 120,
        "speech_rate_max": 250,
        "pause_ratio_max": 0.3,
        "hnr_min": 18,
        "pronunciation_accuracy_min": 0.7
    },
    "advanced": {
        "pitch_range_min": 100,
        "speech_rate_min": 150,
        "speech_rate_max": 220,
        "pause_ratio_max": 0.25,
        "hnr_min": 20,
        "pronunciation_accuracy_min": 0.8
    }
}