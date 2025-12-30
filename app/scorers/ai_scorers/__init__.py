"""
AI-based scorers package
Supports OpenAI and Gemini for STT and NLP analysis
"""
from app.scorers.ai_scorers.ai_provider import AIProvider, AIProviderType
from app.scorers.ai_scorers.task_achievement_scorer import TaskAchievementScorer
from app.scorers.ai_scorers.grammar_scorer import GrammarScorer
from app.scorers.ai_scorers.vocabulary_scorer import VocabularyScorer
from app.scorers.ai_scorers.coherence_scorer import CoherenceScorer

__all__ = [
    "AIProvider",
    "AIProviderType",
    "TaskAchievementScorer",
    "GrammarScorer", 
    "VocabularyScorer",
    "CoherenceScorer"
]
