"""
Audio Processing Constants
"""

# Sample rate for audio processing
AUDIO_SAMPLE_RATE = 16000  # Standard sample rate for speech processing

# Audio normalization
AUDIO_NORMALIZE_MAX = 0.9  # Maximum amplitude after normalization

# Hashing for unique filenames
AUDIO_HASH_LENGTH = 8  # Length of MD5 hash prefix
AUDIO_HASH_PREFIX_BYTES = 1000  # Number of bytes to hash from audio content

# Praat processing
PRAAT_TIMEOUT_SECONDS = 60  # Timeout for Praat script execution
PRAAT_PCM_SUBTYPE = 'PCM_16'  # WAV subtype for Praat

# MIME types for audio files
AUDIO_MIME_TYPES = {
    ".wav": "audio/wav",
    ".mp3": "audio/mp3",
    ".m4a": "audio/m4a",
    ".flac": "audio/flac"
}
