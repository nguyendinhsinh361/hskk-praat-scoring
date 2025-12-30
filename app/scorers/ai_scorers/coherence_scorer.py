"""
Coherence Scorer - Evaluate text coherence and cohesion
Uses AI (NLP) for logical flow analysis
"""
from typing import Dict, Any

from app.scorers.base_scorer import BaseScorer, ScoringResult, ScoreLevel
from app.scorers.ai_scorers.ai_provider import AIProvider


class CoherenceScorer(BaseScorer):
    """
    Score coherence and cohesion using AI analysis.
    
    Evaluates:
    - Logical flow of ideas
    - Use of transition words
    - Overall text structure
    """
    
    def __init__(self, ai_provider: AIProvider, exam_level: str = "beginner"):
        self.ai_provider = ai_provider
        super().__init__(exam_level)
    
    def _load_thresholds(self) -> None:
        """Load scoring thresholds"""
        self.max_scores = {
            "beginner": {"task3": 2.0},
            "intermediate": {"task2": 1.0, "task3": 2.0},
            "advanced": {"task3": 3.0}
        }
    
    def get_criteria_name(self) -> str:
        return "Tính mạch lạc và liên kết (Coherence and Cohesion)"
    
    async def score(
        self,
        data: Dict[str, Any],
        task: str = "task3"
    ) -> ScoringResult:
        """
        Score coherence from transcribed text
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
        
        # Analyze coherence using AI
        analysis = await self.ai_provider.analyze_text(
            text,
            analysis_type="coherence"
        )
        
        coherence = analysis.get("coherence_score", 0)
        has_transitions = analysis.get("has_transitions", False)
        logical_flow = analysis.get("logical_flow", False)
        feedback = analysis.get("feedback", "")
        
        # Calculate score
        base_score = coherence / 100 * max_score
        
        # Bonus for transitions and logical flow
        if has_transitions:
            base_score = min(max_score, base_score * 1.1)
        if not logical_flow:
            base_score *= 0.8
        
        score = min(max_score, max(0, base_score))
        level = self._determine_level(score, max_score)
        
        issues = []
        if not has_transitions:
            issues.append("Thiếu từ liên kết giữa các ý")
        if not logical_flow:
            issues.append("Các ý chưa liên kết logic")
        if coherence < 50:
            issues.append("Nội dung rời rạc, thiếu mạch lạc")
        
        return ScoringResult(
            score=round(score, 2),
            max_score=max_score,
            level=level,
            issues=issues,
            feedback=feedback or self._generate_feedback(level),
            details={
                "coherence_score": coherence,
                "has_transitions": has_transitions,
                "logical_flow": logical_flow
            }
        )
    
    def _generate_feedback(self, level: ScoreLevel) -> str:
        """Generate Vietnamese feedback"""
        feedbacks = {
            ScoreLevel.EXCELLENT: "Ý tưởng rõ ràng, liên kết chặt chẽ, logic. Có ví dụ hợp lý.",
            ScoreLevel.GOOD: "Ý tưởng phát triển tốt, sắp xếp hợp lý.",
            ScoreLevel.ACCEPTABLE: "Ý tưởng cơ bản rõ ràng nhưng thiếu liên kết mạch lạc.",
            ScoreLevel.POOR: "Ý tưởng không hợp lý, thiếu liên kết. Nội dung rời rạc."
        }
        return feedbacks.get(level, "")
