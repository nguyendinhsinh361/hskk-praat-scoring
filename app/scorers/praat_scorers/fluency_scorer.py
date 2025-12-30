"""
Fluency Scorer - Score speech fluency using Praat timing metrics
Based on speech rate, pause patterns, and articulation
"""
from typing import Dict, Any, List

from app.scorers.base_scorer import BaseScorer, ScoringResult, ScoreLevel


class FluencyScorer(BaseScorer):
    """
    Score fluency based on Praat timing features.
    
    Primary metrics:
    - speech_rate: Syllables per minute (including pauses)
    - pause_ratio: Ratio of pause time to total time
    - num_pauses: Number of pauses
    - mean_pause_duration: Average pause length
    
    Secondary metrics:
    - articulation_rate: Speaking rate without pauses
    - speech_duration: Actual speaking time
    - pause_duration: Total pause time
    """
    
    def _load_thresholds(self) -> None:
        """Load thresholds based on exam level"""
        self.thresholds = {
            "speech_rate_slow": 100,
            "speech_rate_ideal_min": 150,
            "speech_rate_ideal_max": 220,
            "speech_rate_fast": 280,
            "pause_ratio_excellent": 0.15,
            "pause_ratio_acceptable": 0.25,
            "pause_ratio_poor": 0.35,
            "mean_pause_excellent": 0.3,
            "mean_pause_acceptable": 0.6,
            "num_pauses_threshold": 10  # per 30s of speech
        }
        
        # Max score varies by exam level and task
        self.max_scores = {
            "beginner": {"task1": 0.5, "task2": 0.5, "task3": 2.0},
            "intermediate": {"task1": 0.5, "task2": 2.0, "task3": 2.0},
            "advanced": {"task1": 2.0, "task2": 5.0, "task3": 3.0}
        }
    
    def get_criteria_name(self) -> str:
        return "Độ trôi chảy (Fluency)"
    
    def score(self, data: Dict[str, Any], task: str = "task1") -> ScoringResult:
        """
        Score fluency based on Praat timing features
        
        Args:
            data: Dictionary containing Praat features
            task: Task identifier (task1, task2, task3)
            
        Returns:
            ScoringResult with fluency score and detected issues
        """
        # Extract metrics
        speech_rate = data.get("speech_rate", 0)
        pause_ratio = data.get("pause_ratio", 1)
        num_pauses = data.get("num_pauses", 0)
        mean_pause_duration = data.get("mean_pause_duration", 0)
        articulation_rate = data.get("articulation_rate", 0)
        duration = data.get("duration", 1)
        
        # Normalize num_pauses to 30s equivalent
        normalized_pauses = (num_pauses / duration) * 30 if duration > 0 else num_pauses
        
        # Determine max score for this task/level
        max_score = self.max_scores.get(self.exam_level, {}).get(task, 1.0)
        
        # Detect issues
        issues: List[str] = []
        detected_problems: List[str] = []
        
        # Check speech rate
        rate_issue = self._check_speech_rate(speech_rate)
        if rate_issue:
            issues.append(rate_issue)
        
        # Check pause patterns
        pause_issues = self._check_pause_patterns(
            pause_ratio, num_pauses, mean_pause_duration, normalized_pauses
        )
        issues.extend(pause_issues["issues"])
        detected_problems.extend(pause_issues["problems"])
        
        # Check speed stability
        speed_diff = abs(articulation_rate - speech_rate)
        if speed_diff > 50:
            issues.append("Tốc độ nói không ổn định")
            detected_problems.append("toc_do_khong_on_dinh")
        
        # Calculate score based on issues
        if not issues:
            score = max_score
            level = ScoreLevel.EXCELLENT
        elif len(issues) == 1:
            score = max_score * 0.75
            level = ScoreLevel.GOOD
        elif len(issues) == 2:
            score = max_score * 0.5
            level = ScoreLevel.ACCEPTABLE
        else:
            score = max_score * 0.25
            level = ScoreLevel.POOR
        
        # Generate feedback
        feedback = self._generate_feedback(level, issues)
        
        return ScoringResult(
            score=round(score, 2),
            max_score=max_score,
            level=level,
            issues=issues,
            feedback=feedback,
            details={
                "speech_rate": speech_rate,
                "pause_ratio": round(pause_ratio, 3),
                "num_pauses": num_pauses,
                "mean_pause_duration": round(mean_pause_duration, 3),
                "articulation_rate": articulation_rate,
                "speed_stability": round(speed_diff, 2),
                "detected_problems": detected_problems
            }
        )
    
    def _check_speech_rate(self, rate: float) -> str:
        """Check if speech rate is within ideal range"""
        if rate < self.thresholds["speech_rate_slow"]:
            return "Tốc độ nói quá chậm"
        elif rate < self.thresholds["speech_rate_ideal_min"]:
            return "Tốc độ nói hơi chậm"
        elif rate > self.thresholds["speech_rate_fast"]:
            return "Tốc độ nói quá nhanh"
        elif rate > self.thresholds["speech_rate_ideal_max"]:
            return "Tốc độ nói hơi nhanh"
        return ""
    
    def _check_pause_patterns(
        self, 
        pause_ratio: float, 
        num_pauses: int,
        mean_pause: float,
        normalized_pauses: float
    ) -> Dict[str, List[str]]:
        """Check pause patterns and return detected issues"""
        issues = []
        problems = []
        
        # Wrong pause (too much pause or too long)
        if pause_ratio > self.thresholds["pause_ratio_acceptable"]:
            issues.append("Ngắt nghỉ quá nhiều")
            problems.append("ngat_nghi_sai")
        elif mean_pause > self.thresholds["mean_pause_acceptable"]:
            issues.append("Thời gian ngắt nghỉ quá dài")
            problems.append("ngat_nghi_sai")
        
        # Hesitation (many short pauses)
        if normalized_pauses > self.thresholds["num_pauses_threshold"] and mean_pause < 0.5:
            issues.append("Ngập ngừng nhiều lần")
            problems.append("ngap_ngung")
        
        return {"issues": issues, "problems": problems}
    
    def _generate_feedback(self, level: ScoreLevel, issues: List[str]) -> str:
        """Generate Vietnamese feedback based on scoring results"""
        
        if level == ScoreLevel.EXCELLENT:
            return "Tốc độ lời nói ổn định, không có ngập ngừng đáng kể. Ngữ điệu tự nhiên."
        elif level == ScoreLevel.GOOD:
            return f"Độ trôi chảy tốt, có một điểm cần cải thiện: {issues[0] if issues else ''}."
        elif level == ScoreLevel.ACCEPTABLE:
            feedback = "Mạch lời nói cơ bản đạt yêu cầu. Cần cải thiện: "
            feedback += "; ".join(issues[:2])
            return feedback
        else:
            feedback = "Mạch lời nói rời rạc, thiếu sự điều tiết về nhịp và cao độ. "
            feedback += "Các vấn đề: " + "; ".join(issues)
            return feedback
