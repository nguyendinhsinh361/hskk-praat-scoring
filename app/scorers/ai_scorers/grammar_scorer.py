"""
Grammar Scorer - Evaluate grammatical accuracy and complexity
Uses AI (NLP) for Chinese grammar analysis
"""
from typing import Dict, Any, List

from app.scorers.base_scorer import BaseScorer, ScoringResult, ScoreLevel
from app.scorers.ai_scorers.ai_provider import AIProvider


class GrammarScorer(BaseScorer):
    """
    Score grammatical accuracy and complexity using AI analysis.
    
    Evaluates:
    - Basic grammar accuracy (no errors)
    - Sentence structure complexity
    - Use of various grammatical patterns
    """
    
    def __init__(self, ai_provider: AIProvider, exam_level: str = "beginner"):
        self.ai_provider = ai_provider
        super().__init__(exam_level)
    
    def _load_thresholds(self) -> None:
        """Load scoring thresholds"""
        self.deduction_per_error = {
            "beginner": 0.25,
            "intermediate": 0.5,
            "advanced": 0.5
        }
        
        # Max score varies by exam level and task
        self.max_scores = {
            "beginner": {"task2": 0.5, "task3": 4.0},
            "intermediate": {"task2": 3.0, "task3": 4.0},
            "advanced": {"task1": 2.0, "task3": 4.0}
        }
    
    def get_criteria_name(self) -> str:
        return "Độ chính xác của ngữ pháp (Grammatical Accuracy)"
    
    async def score(
        self,
        data: Dict[str, Any],
        task: str = "task2"
    ) -> ScoringResult:
        """
        Score grammar from transcribed text
        
        Args:
            data: Dictionary with "text" key containing transcribed text
            task: Task type
            
        Returns:
            ScoringResult with grammar score
        """
        text = data.get("text", "")
        max_score = self.max_scores.get(self.exam_level, {}).get(task, 2.0)
        deduction = self.deduction_per_error.get(self.exam_level, 0.5)
        
        if not text:
            return ScoringResult(
                score=0,
                max_score=max_score,
                level=ScoreLevel.POOR,
                issues=["Không có nội dung để đánh giá"],
                feedback="Không phát hiện được nội dung.",
                details={}
            )
        
        # Analyze grammar using AI
        analysis = await self.ai_provider.analyze_text(
            text,
            analysis_type="grammar"
        )
        
        errors = analysis.get("errors", [])
        accuracy_score = analysis.get("accuracy_score", 0)
        complexity_score = analysis.get("complexity_score", 0)
        feedback = analysis.get("feedback", "")
        
        # Calculate score
        # Base: accuracy contributes 70%, complexity 30%
        base_accuracy = max_score * 0.7
        base_complexity = max_score * 0.3
        
        # Deduct for errors
        error_count = len(errors)
        accuracy_deduction = min(error_count * deduction, base_accuracy)
        
        accuracy_part = max(0, base_accuracy * (accuracy_score / 100) - accuracy_deduction)
        complexity_part = base_complexity * (complexity_score / 100) if complexity_score > 50 else 0
        
        score = accuracy_part + complexity_part
        score = min(max_score, max(0, score))
        
        level = self._determine_level(score, max_score)
        
        # Generate issues list
        issues = []
        if error_count > 0:
            issues.append(f"Phát hiện {error_count} lỗi ngữ pháp")
            for err in errors[:3]:  # List first 3 errors
                issues.append(f"- {err}")
        if complexity_score < 50:
            issues.append("Cấu trúc câu đơn giản, thiếu đa dạng")
        
        return ScoringResult(
            score=round(score, 2),
            max_score=max_score,
            level=level,
            issues=issues,
            feedback=feedback or self._generate_feedback(level, error_count),
            details={
                "error_count": error_count,
                "errors": errors,
                "accuracy_score": accuracy_score,
                "complexity_score": complexity_score
            }
        )
    
    def _generate_feedback(self, level: ScoreLevel, error_count: int) -> str:
        """Generate Vietnamese feedback"""
        if level == ScoreLevel.EXCELLENT:
            return "Không mắc lỗi ngữ pháp cơ bản. Sử dụng linh hoạt nhiều cấu trúc câu."
        elif level == ScoreLevel.GOOD:
            return f"Ngữ pháp cơ bản chính xác, có {error_count} lỗi nhỏ cần cải thiện."
        elif level == ScoreLevel.ACCEPTABLE:
            return f"Có {error_count} lỗi ngữ pháp. Cần ôn lại các cấu trúc cơ bản."
        else:
            return "Nhiều lỗi ngữ pháp cơ bản. Cần luyện tập thêm các mẫu câu thường dùng."
