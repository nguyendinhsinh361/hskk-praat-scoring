"""
Scoring Constants - Thresholds, weights, and scoring parameters
"""

# ========== Pronunciation Thresholds ==========
# HNR (Harmonics-to-Noise Ratio) - Voice clarity
HNR_EXCELLENT = 20.0  # Excellent voice clarity
HNR_GOOD = 15.0  # Good clarity
HNR_POOR = 10.0  # Poor clarity threshold

# Jitter - Voice frequency stability
JITTER_EXCELLENT = 0.01  # Excellent stability
JITTER_ACCEPTABLE = 0.015  # Acceptable jitter
JITTER_POOR = 0.02  # Poor stability threshold

# Shimmer - Amplitude consistency
SHIMMER_EXCELLENT = 0.05  # Excellent consistency
SHIMMER_ACCEPTABLE = 0.08  # Acceptable shimmer
SHIMMER_POOR = 0.12  # Poor consistency threshold

# ========== Fluency Thresholds ==========
# Speech rate (syllables per minute)
SPEECH_RATE_SLOW = 100  # Too slow
SPEECH_RATE_IDEAL_MIN = 150  # Ideal range minimum
SPEECH_RATE_IDEAL_MAX = 220  # Ideal range maximum
SPEECH_RATE_FAST = 280  # Too fast

# Pause ratio (pause time / total time)
PAUSE_RATIO_EXCELLENT = 0.15  # Excellent
PAUSE_RATIO_ACCEPTABLE = 0.25  # Acceptable
PAUSE_RATIO_POOR = 0.35  # Poor

# Mean pause duration (seconds)
MEAN_PAUSE_EXCELLENT = 0.3  # Excellent
MEAN_PAUSE_ACCEPTABLE = 0.6  # Acceptable
HESITATION_PAUSE_THRESHOLD = 0.5  # For detecting hesitation

# Number of pauses per 30 seconds
NUM_PAUSES_THRESHOLD = 10  # Threshold for too many pauses
FLUENCY_NORMALIZE_DURATION = 30  # Normalize pauses to 30s

# Speed stability
SPEED_STABILITY_THRESHOLD = 50  # Hz difference between articulation and speech rate

# ========== Scoring Deduction Weights ==========
DEDUCTION_MINOR = 0.15  # Minor issue
DEDUCTION_MODERATE = 0.25  # Moderate issue
DEDUCTION_MAJOR = 0.35  # Major issue
DEDUCTION_SEVERE = 0.5  # Severe issue

# ========== Score Multipliers ==========
SCORE_MULTIPLIER_EXCELLENT = 1.0  # 100% of max score
SCORE_MULTIPLIER_GOOD = 0.75  # 75% of max score
SCORE_MULTIPLIER_ACCEPTABLE = 0.5  # 50% of max score
SCORE_MULTIPLIER_POOR = 0.25  # 25% of max score

# ========== Word Analysis Thresholds ==========
# (Already defined in word_analysis_service.py, keeping reference)
DEFAULT_PITCH_MEAN = 200.0  # Hz
DEFAULT_HNR_MEAN = 15.0  # dB
PITCH_DEVIATION_THRESHOLD = 0.5  # 50% deviation from mean
PITCH_STD_THRESHOLD = 50.0  # Hz, high std = unstable tone
HNR_POOR_THRESHOLD = 8.0  # Below this = poor voice quality
HNR_LOW_RATIO = 0.6  # Below 60% of mean = low clarity
MAX_WORDS_IN_GPT_DETAIL = 30  # Limit words shown to GPT

# ========== Percentage Thresholds ==========
PERCENTAGE_ROUNDING = 1  # Decimal places for percentage
EXCELLENT_PERCENTAGE_THRESHOLD = 80  # Above 80% = excellent pronunciation

# ========== Max Scores by Level and Task ==========
PRONUNCIATION_MAX_SCORES = {
    "beginner": {"task1": 0.5, "task2": 0.5, "task3": 4.0, "task": 10.0},
    "intermediate": {"task1": 1.0, "task2": 3.0, "task3": 4.0, "task": 10.0},
    "advanced": {"task1": 2.0, "task2": 5.0, "task3": 5.0, "task": 10.0}
}

FLUENCY_MAX_SCORES = {
    "beginner": {"task1": 0.5, "task2": 0.5, "task3": 2.0, "task": 10.0},
    "intermediate": {"task1": 0.5, "task2": 2.0, "task3": 2.0, "task": 10.0},
    "advanced": {"task1": 2.0, "task2": 5.0, "task3": 3.0, "task": 10.0}
}
