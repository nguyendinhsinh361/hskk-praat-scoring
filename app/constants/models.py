"""
AI Model Constants - Model names, versions, and configurations
"""

# ========== OpenAI Whisper ==========
WHISPER_MODEL = "whisper-1"
WHISPER_LANGUAGE = "zh"  # Chinese
WHISPER_TEMPERATURE = 0  # Deterministic output

# ========== FunASR ==========
FUNASR_MODEL = "paraformer-zh"
FUNASR_VERSION = "v2.0.4"
FUNASR_DEVICE = "cpu"  # Force CPU for stability
FUNASR_DISABLE_UPDATE = True

# ========== GPT Models ==========
GPT_MODEL_NANO = "gpt-4.1-nano"
GPT_MODEL_MINI = "gpt-4.1-mini"
GPT_MODEL_5_MINI = "gpt-5-mini"
DEFAULT_GPT_MODEL = GPT_MODEL_NANO

# GPT Scoring config
GPT_SCORING_TEMPERATURE = 0  # Deterministic scoring
GPT_WORD_FEEDBACK_TEMPERATURE = 0.7  # More creative for feedback
GPT_WORD_FEEDBACK_MAX_TOKENS = 1500

# ========== Gemini Models ==========
GEMINI_MODEL_FLASH = "gemini-2.0-flash-exp"
GEMINI_MODEL_2_5_FLASH = "gemini-2.5-flash"
GEMINI_MODEL_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
DEFAULT_GEMINI_MODEL = GEMINI_MODEL_2_5_FLASH_LITE

# ========== Default AI Criteria Config ==========
DEFAULT_AI_CRITERIA_CONFIG = {
    "task_achievement": 20,
    "grammar": 15,
    "vocabulary": 10,
    "coherence": 10
}
