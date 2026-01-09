"""
Pronunciation Scorer - Score pronunciation quality using Praat metrics
Based on HNR, jitter, and shimmer values
"""
from typing import Dict, Any, List

from app.scorers.base_scorer import BaseScorer, ScoringResult, ScoreLevel
from app.constants.scoring import (
    HNR_EXCELLENT, HNR_GOOD, HNR_POOR,
    JITTER_EXCELLENT, JITTER_ACCEPTABLE, JITTER_POOR,
    SHIMMER_EXCELLENT, SHIMMER_ACCEPTABLE, SHIMMER_POOR,
    DEDUCTION_MINOR, DEDUCTION_MODERATE, DEDUCTION_MAJOR, DEDUCTION_SEVERE,
    PRONUNCIATION_MAX_SCORES
)
from app.constants.messages import (
    CRITERIA_NAME_PRONUNCIATION,
    FEEDBACK_PRONUNCIATION_EXCELLENT, FEEDBACK_PRONUNCIATION_GOOD,
    FEEDBACK_PRONUNCIATION_ACCEPTABLE_PREFIX, FEEDBACK_PRONUNCIATION_ACCEPTABLE_DEFAULT,
    FEEDBACK_PRONUNCIATION_POOR_PREFIX, FEEDBACK_PRONUNCIATION_POOR_SUFFIX,
    ISSUE_LOW_HNR, ISSUE_NOISY_VOICE, ISSUE_HIGH_JITTER,
    ISSUE_UNSTABLE_VOICE_SEVERE, ISSUE_HIGH_SHIMMER, ISSUE_HIGH_SHIMMER_SEVERE
)


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
        # Thresholds from centralized constants module
        self.thresholds = {
            "hnr_excellent": HNR_EXCELLENT,
            "hnr_good": HNR_GOOD,
            "hnr_poor": HNR_POOR,
            "jitter_excellent": JITTER_EXCELLENT,
            "jitter_acceptable": JITTER_ACCEPTABLE,
            "jitter_poor": JITTER_POOR,
            "shimmer_excellent": SHIMMER_EXCELLENT,
            "shimmer_acceptable": SHIMMER_ACCEPTABLE,
            "shimmer_poor": SHIMMER_POOR
        }
        
        # Max score varies by exam level and task
        self.max_scores = PRONUNCIATION_MAX_SCORES
    
    def get_criteria_name(self) -> str:
        return CRITERIA_NAME_PRONUNCIATION
    
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
            deductions += DEDUCTION_MINOR
        elif hnr >= self.thresholds["hnr_poor"]:
            hnr_quality = "acceptable"
            deductions += DEDUCTION_MODERATE + 0.05
            issues.append(ISSUE_LOW_HNR)
        else:
            hnr_quality = "poor"
            deductions += DEDUCTION_SEVERE
            issues.append(ISSUE_NOISY_VOICE)
        
        # Jitter check (voice stability)
        if jitter <= self.thresholds["jitter_excellent"]:
            jitter_quality = "excellent"
        elif jitter <= self.thresholds["jitter_acceptable"]:
            jitter_quality = "acceptable"
            deductions += DEDUCTION_MINOR
        elif jitter <= self.thresholds["jitter_poor"]:
            jitter_quality = "poor"
            deductions += DEDUCTION_MODERATE
            issues.append(ISSUE_HIGH_JITTER)
        else:
            jitter_quality = "very_poor"
            deductions += DEDUCTION_MAJOR
            issues.append(ISSUE_UNSTABLE_VOICE_SEVERE)
        
        # Shimmer check (amplitude consistency)
        if shimmer <= self.thresholds["shimmer_excellent"]:
            shimmer_quality = "excellent"
        elif shimmer <= self.thresholds["shimmer_acceptable"]:
            shimmer_quality = "acceptable"
            deductions += DEDUCTION_MINOR
        elif shimmer <= self.thresholds["shimmer_poor"]:
            shimmer_quality = "poor"
            deductions += DEDUCTION_MODERATE
            issues.append(ISSUE_HIGH_SHIMMER)
        else:
            shimmer_quality = "very_poor"
            deductions += DEDUCTION_MAJOR
            issues.append(ISSUE_HIGH_SHIMMER_SEVERE)
        
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
            return FEEDBACK_PRONUNCIATION_EXCELLENT
        elif level == ScoreLevel.GOOD:
            return FEEDBACK_PRONUNCIATION_GOOD
        elif level == ScoreLevel.ACCEPTABLE:
            feedback = FEEDBACK_PRONUNCIATION_ACCEPTABLE_PREFIX
            feedback += "; ".join(issues[:2]) if issues else FEEDBACK_PRONUNCIATION_ACCEPTABLE_DEFAULT
            return feedback
        else:
            feedback = FEEDBACK_PRONUNCIATION_POOR_PREFIX
            feedback += FEEDBACK_PRONUNCIATION_POOR_SUFFIX + "; ".join(issues) if issues else ""
            return feedback
