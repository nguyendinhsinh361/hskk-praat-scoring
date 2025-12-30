"""
Pronunciation Scorer - Score pronunciation quality using Praat metrics
Based on HNR, jitter, and shimmer values
"""
from typing import Dict, Any, List

from app.scorers.base_scorer import BaseScorer, ScoringResult, ScoreLevel


class PronunciationScorer(BaseScorer):
    """
    Score pronunciation quality based on Praat acoustic features.
    
    Primary metrics:
    - hnr_mean: Harmonics-to-Noise Ratio (voice clarity)
    - jitter_local: Frequency perturbation (voice stability)
    - shimmer_local: Amplitude perturbation (volume consistency)
    
    Secondary metrics:
    - f1_mean, f2_mean: Formants (vowel quality)
    - pitch_range, pitch_std: Intonation
    """
    
    def _load_thresholds(self) -> None:
        """Load thresholds based on exam level"""
        # Common thresholds from HSKK criteria
        self.thresholds = {
            "hnr_excellent": 20.0,
            "hnr_good": 15.0,
            "hnr_poor": 10.0,
            "jitter_excellent": 0.01,
            "jitter_acceptable": 0.015,
            "jitter_poor": 0.02,
            "shimmer_excellent": 0.05,
            "shimmer_acceptable": 0.08,
            "shimmer_poor": 0.12
        }
        
        # Max score varies by exam level and task
        self.max_scores = {
            "beginner": {"task1": 0.5, "task2": 0.5, "task3": 4.0},
            "intermediate": {"task1": 1.0, "task2": 3.0, "task3": 4.0},
            "advanced": {"task1": 2.0, "task2": 5.0, "task3": 5.0}
        }
    
    def get_criteria_name(self) -> str:
        return "Phát âm (Pronunciation)"
    
    def score(self, data: Dict[str, Any], task: str = "task1") -> ScoringResult:
        """
        Score pronunciation based on Praat features
        
        Args:
            data: Dictionary containing Praat features
            task: Task identifier (task1, task2, task3)
            
        Returns:
            ScoringResult with pronunciation score and feedback
        """
        # Extract primary metrics
        hnr = data.get("hnr_mean", 0)
        jitter = data.get("jitter_local", 1)
        shimmer = data.get("shimmer_local", 1)
        
        # Extract secondary metrics for detailed feedback
        pitch_range = data.get("pitch_range", 0)
        pitch_std = data.get("pitch_std", 0)
        f1_mean = data.get("f1_mean", 0)
        f2_mean = data.get("f2_mean", 0)
        
        # Determine max score for this task/level
        max_score = self.max_scores.get(self.exam_level, {}).get(task, 1.0)
        
        # Calculate base score
        issues: List[str] = []
        deductions = 0.0
        
        # HNR check (voice clarity)
        if hnr >= self.thresholds["hnr_excellent"]:
            hnr_quality = "excellent"
        elif hnr >= self.thresholds["hnr_good"]:
            hnr_quality = "good"
            deductions += 0.15
        elif hnr >= self.thresholds["hnr_poor"]:
            hnr_quality = "acceptable"
            deductions += 0.3
            issues.append("Độ trong của giọng chưa tốt (HNR thấp)")
        else:
            hnr_quality = "poor"
            deductions += 0.5
            issues.append("Giọng nói có nhiều nhiễu, thiếu độ trong")
        
        # Jitter check (voice stability)
        if jitter <= self.thresholds["jitter_excellent"]:
            jitter_quality = "excellent"
        elif jitter <= self.thresholds["jitter_acceptable"]:
            jitter_quality = "acceptable"
            deductions += 0.15
        elif jitter <= self.thresholds["jitter_poor"]:
            jitter_quality = "poor"
            deductions += 0.25
            issues.append("Tần số giọng không ổn định (jitter cao)")
        else:
            jitter_quality = "very_poor"
            deductions += 0.35
            issues.append("Giọng nói thiếu ổn định nghiêm trọng")
        
        # Shimmer check (amplitude consistency)
        if shimmer <= self.thresholds["shimmer_excellent"]:
            shimmer_quality = "excellent"
        elif shimmer <= self.thresholds["shimmer_acceptable"]:
            shimmer_quality = "acceptable"
            deductions += 0.15
        elif shimmer <= self.thresholds["shimmer_poor"]:
            shimmer_quality = "poor"
            deductions += 0.25
            issues.append("Âm lượng không đều (shimmer cao)")
        else:
            shimmer_quality = "very_poor"
            deductions += 0.35
            issues.append("Âm lượng biến thiên quá lớn")
        
        # Calculate final score
        score = max(0, max_score * (1 - deductions))
        level = self._determine_level(score, max_score)
        
        # Generate feedback
        feedback = self._generate_feedback(level, issues, hnr_quality, jitter_quality, shimmer_quality)
        
        return ScoringResult(
            score=round(score, 2),
            max_score=max_score,
            level=level,
            issues=issues,
            feedback=feedback,
            details={
                "hnr_mean": hnr,
                "hnr_quality": hnr_quality,
                "jitter_local": jitter,
                "jitter_quality": jitter_quality,
                "shimmer_local": shimmer,
                "shimmer_quality": shimmer_quality,
                "pitch_range": pitch_range,
                "pitch_std": pitch_std,
                "f1_mean": f1_mean,
                "f2_mean": f2_mean
            }
        )
    
    def _generate_feedback(
        self, 
        level: ScoreLevel, 
        issues: List[str],
        hnr_quality: str,
        jitter_quality: str,
        shimmer_quality: str
    ) -> str:
        """Generate Vietnamese feedback based on scoring results"""
        
        if level == ScoreLevel.EXCELLENT:
            return "Phát âm rõ ràng, không có lỗi sai. Giọng đọc tự nhiên, gần với chuẩn phổ thông."
        elif level == ScoreLevel.GOOD:
            return "Phát âm tương đối tốt, có một vài điểm cần cải thiện nhỏ."
        elif level == ScoreLevel.ACCEPTABLE:
            feedback = "Phát âm cơ bản đạt yêu cầu nhưng cần cải thiện: "
            feedback += "; ".join(issues[:2]) if issues else "độ ổn định của giọng"
            return feedback
        else:
            feedback = "Mức độ kiểm soát cơ quan phát âm chưa tốt. "
            feedback += "Các vấn đề cần khắc phục: " + "; ".join(issues) if issues else ""
            return feedback
