"""
Vocabulary Scorer - Evaluate vocabulary diversity and accuracy
Uses AI (NLP) for Chinese vocabulary analysis
"""
from typing import Dict, Any

from app.scorers.base_scorer import BaseScorer, ScoringResult, ScoreLevel
from app.scorers.ai_scorers.ai_provider import AIProvider


class VocabularyScorer(BaseScorer):
    """
    Score vocabulary usage using AI analysis.
    
    Evaluates:
    - Vocabulary diversity
    - Word usage accuracy
    - HSK level appropriateness
    """
    
    def __init__(self, ai_provider: AIProvider, exam_level: str = "beginner"):
        self.ai_provider = ai_provider
        super().__init__(exam_level)
    
    def _load_thresholds(self) -> None:
        """Load scoring thresholds"""
        # Max score varies by exam level and task
        self.max_scores = {
            "beginner": {"task3": 2.0},
            "intermediate": {"task2": 1.0, "task3": 2.0},
            "advanced": {"task3": 2.0}
        }
    
    def get_criteria_name(self) -> str:
        return "Vốn từ vựng (Lexical Resource)"
    
    async def score(
        self,
        data: Dict[str, Any],
        task: str = "task3"
    ) -> ScoringResult:
        """
        Score vocabulary from transcribed text
        """
        text = data.get("text", "")
        max_score = self.max_scores.get(self.exam_level, {}).get(task, 2.0)
        
        if not text:
            return ScoringResult(
                score=0,
                max_score=max_score,
                level=ScoreLevel.POOR,
                issues=["Không có nội dung để đánh giá"],
                feedback="Không phát hiện được nội dung.",
                details={}
            )
        
        # Analyze vocabulary using AI
        analysis = await self.ai_provider.analyze_text(
            text,
            analysis_type="vocabulary"
        )
        
        diversity = analysis.get("diversity_score", 0)
        accuracy = analysis.get("accuracy_score", 0)
        hsk_match = analysis.get("hsk_level_match", True)
        feedback = analysis.get("feedback", "")
        
        # Calculate score (diversity 60%, accuracy 40%)
        combined = diversity * 0.6 + accuracy * 0.4
        
        if combined >= 80 and hsk_match:
            score = max_score
            level = ScoreLevel.EXCELLENT
        elif combined >= 60:
            score = max_score * 0.75
            level = ScoreLevel.GOOD
        elif combined >= 40:
            score = max_score * 0.5
            level = ScoreLevel.ACCEPTABLE
        else:
            score = max_score * 0.25
            level = ScoreLevel.POOR
        
        issues = []
        if diversity < 60:
            issues.append("Từ vựng đơn giản, thiếu đa dạng")
        if accuracy < 70:
            issues.append("Sử dụng từ chưa chính xác")
        if not hsk_match:
            issues.append("Từ vựng chưa phù hợp với cấp độ HSK")
        
        return ScoringResult(
            score=round(score, 2),
            max_score=max_score,
            level=level,
            issues=issues,
            feedback=feedback or self._generate_feedback(level),
            details={
                "diversity_score": diversity,
                "accuracy_score": accuracy,
                "hsk_level_match": hsk_match
            }
        )
    
    def _generate_feedback(self, level: ScoreLevel) -> str:
        """Generate Vietnamese feedback"""
        feedbacks = {
            ScoreLevel.EXCELLENT: "Sử dụng từ vựng phong phú, linh hoạt, chính xác.",
            ScoreLevel.GOOD: "Từ vựng phù hợp và chính xác, có thể mở rộng thêm.",
            ScoreLevel.ACCEPTABLE: "Sử dụng từ vựng chính xác nhưng đơn giản, cơ bản.",
            ScoreLevel.POOR: "Vốn từ vựng hạn chế, cần mở rộng thêm."
        }
        return feedbacks.get(level, "")
