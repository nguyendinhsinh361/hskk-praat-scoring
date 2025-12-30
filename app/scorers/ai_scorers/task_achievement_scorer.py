"""
Task Achievement Scorer - Evaluate if response meets task requirements
Uses AI (STT + NLP) for content analysis
"""
from typing import Dict, Any, Optional
from pathlib import Path

from app.scorers.base_scorer import BaseScorer, ScoringResult, ScoreLevel
from app.scorers.ai_scorers.ai_provider import AIProvider


class TaskAchievementScorer(BaseScorer):
    """
    Score task achievement using AI analysis.
    
    Evaluates:
    - Content relevance to topic/question
    - Completeness of response
    - Similarity to reference (for repeat tasks)
    """
    
    def __init__(self, ai_provider: AIProvider, exam_level: str = "beginner"):
        self.ai_provider = ai_provider
        super().__init__(exam_level)
    
    def _load_thresholds(self) -> None:
        """Load scoring thresholds"""
        self.similarity_thresholds = {
            "excellent": 90,  # >= 90% similarity
            "good": 70,       # >= 70%
            "acceptable": 50, # >= 50%
            "poor": 0         # < 50%
        }
        
        # Max score varies by exam level and task
        self.max_scores = {
            "beginner": {"task1": 1.0, "task2": 1.5, "task3": 6.0},
            "intermediate": {"task1": 1.5, "task2": 5.0, "task3": 6.0},
            "advanced": {"task1": 4.0, "task2": 10.0, "task3": 8.0}
        }
    
    def get_criteria_name(self) -> str:
        return "Khả năng hoàn thành yêu cầu của bài (Task Achievement)"
    
    async def score_from_audio(
        self,
        audio_path: Path,
        task: str = "task1",
        reference_text: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ScoringResult:
        """
        Score task achievement from audio file
        
        Args:
            audio_path: Path to audio file
            task: Task type (task1=repeat, task2=describe, task3=answer)
            reference_text: Reference text for comparison (task1)
            context: Additional context (question, image description, etc.)
            
        Returns:
            ScoringResult with achievement score
        """
        # Step 1: Transcribe audio
        transcribed_text = await self.ai_provider.transcribe(audio_path)
        
        # Step 2: Score based on task type
        return await self.score(
            {"text": transcribed_text},
            task=task,
            reference_text=reference_text,
            context=context
        )
    
    async def score(
        self,
        data: Dict[str, Any],
        task: str = "task1",
        reference_text: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ScoringResult:
        """
        Score task achievement from transcribed text
        """
        text = data.get("text", "")
        max_score = self.max_scores.get(self.exam_level, {}).get(task, 1.0)
        
        if not text:
            return ScoringResult(
                score=0,
                max_score=max_score,
                level=ScoreLevel.POOR,
                issues=["Không có nội dung"],
                feedback="Không phát hiện được nội dung trả lời.",
                details={"transcribed_text": ""}
            )
        
        # Different scoring based on task type
        if task == "task1" and reference_text:
            # Repeat/Read task - compare with reference
            return await self._score_similarity(text, reference_text, max_score)
        else:
            # Answer task - evaluate relevance and completeness
            return await self._score_task_achievement(
                text, max_score, context or {}
            )
    
    async def _score_similarity(
        self,
        spoken_text: str,
        reference_text: str,
        max_score: float
    ) -> ScoringResult:
        """Score based on similarity to reference"""
        analysis = await self.ai_provider.analyze_text(
            spoken_text,
            analysis_type="similarity",
            reference_text=reference_text
        )
        
        similarity = analysis.get("similarity_percentage", 0)
        missing = analysis.get("missing_content", [])
        feedback = analysis.get("feedback", "")
        
        # Calculate score based on similarity percentage
        if similarity >= self.similarity_thresholds["excellent"]:
            score = max_score
            level = ScoreLevel.EXCELLENT
        elif similarity >= self.similarity_thresholds["good"]:
            score = max_score * 0.75
            level = ScoreLevel.GOOD
        elif similarity >= self.similarity_thresholds["acceptable"]:
            score = max_score * 0.5
            level = ScoreLevel.ACCEPTABLE
        else:
            score = max_score * 0.25
            level = ScoreLevel.POOR
        
        issues = []
        if missing:
            issues.append(f"Thiếu nội dung: {', '.join(missing[:3])}")
        
        return ScoringResult(
            score=round(score, 2),
            max_score=max_score,
            level=level,
            issues=issues,
            feedback=feedback or self._generate_similarity_feedback(level, similarity),
            details={
                "similarity_percentage": similarity,
                "missing_content": missing,
                "transcribed_text": spoken_text
            }
        )
    
    async def _score_task_achievement(
        self,
        text: str,
        max_score: float,
        context: Dict[str, Any]
    ) -> ScoringResult:
        """Score task achievement for answer tasks"""
        analysis = await self.ai_provider.analyze_text(
            text,
            analysis_type="task_achievement",
            context=context
        )
        
        relevance = analysis.get("relevance_score", 0)
        completeness = analysis.get("completeness_score", 0)
        feedback = analysis.get("feedback", "")
        
        # Combined score
        combined = (relevance * 0.6 + completeness * 0.4)
        
        if combined >= 85:
            level = ScoreLevel.EXCELLENT
            score = max_score
        elif combined >= 70:
            level = ScoreLevel.GOOD
            score = max_score * 0.75
        elif combined >= 50:
            level = ScoreLevel.ACCEPTABLE
            score = max_score * 0.5
        else:
            level = ScoreLevel.POOR
            score = max_score * 0.25
        
        issues = []
        if relevance < 70:
            issues.append("Câu trả lời chưa đúng trọng tâm")
        if completeness < 70:
            issues.append("Nội dung chưa đầy đủ")
        
        return ScoringResult(
            score=round(score, 2),
            max_score=max_score,
            level=level,
            issues=issues,
            feedback=feedback or self._generate_achievement_feedback(level),
            details={
                "relevance_score": relevance,
                "completeness_score": completeness,
                "transcribed_text": text
            }
        )
    
    def _generate_similarity_feedback(self, level: ScoreLevel, similarity: float) -> str:
        """Generate feedback for similarity scoring"""
        feedbacks = {
            ScoreLevel.EXCELLENT: "Câu được lặp lại gần như trùng khớp với bản gốc, không xuất hiện nhiều lỗi bỏ sót hoặc thay đổi trật tự.",
            ScoreLevel.GOOD: f"Thí sinh nhắc lại được {similarity:.0f}% nội dung, cần cải thiện độ chính xác.",
            ScoreLevel.ACCEPTABLE: "Thí sinh cơ bản hiểu và lặp lại được nội dung chính, tuy nhiên vẫn tồn tại lỗi sai hoặc thiếu sót.",
            ScoreLevel.POOR: "Thí sinh gặp khó khăn trong việc tái hiện chính xác câu nghe được."
        }
        return feedbacks.get(level, "")
    
    def _generate_achievement_feedback(self, level: ScoreLevel) -> str:
        """Generate feedback for task achievement"""
        feedbacks = {
            ScoreLevel.EXCELLENT: "Phần trả lời đầy đủ, rõ ràng, đúng trọng tâm, thể hiện khả năng lập luận tốt.",
            ScoreLevel.GOOD: "Đúng chủ đề, nội dung tương đối đầy đủ, một vài điểm có thể cải thiện.",
            ScoreLevel.ACCEPTABLE: "Đúng chủ đề, độ dài phù hợp nhưng nội dung còn đơn giản.",
            ScoreLevel.POOR: "Chưa đủ thông tin, cấu trúc chưa hoàn chỉnh, không đúng trọng tâm."
        }
        return feedbacks.get(level, "")
