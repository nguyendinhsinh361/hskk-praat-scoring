"""
Fluency Scorer - Score speech fluency using Praat timing metrics
Based on speech rate, pause patterns, and articulation
"""
from typing import Dict, Any, List

from app.scorers.base_scorer import BaseScorer, ScoringResult, ScoreLevel
from app.constants.scoring import (
    SPEECH_RATE_SLOW, SPEECH_RATE_IDEAL_MIN, SPEECH_RATE_IDEAL_MAX, SPEECH_RATE_FAST,
    PAUSE_RATIO_EXCELLENT, PAUSE_RATIO_ACCEPTABLE, PAUSE_RATIO_POOR,
    MEAN_PAUSE_EXCELLENT, MEAN_PAUSE_ACCEPTABLE, HESITATION_PAUSE_THRESHOLD,
    NUM_PAUSES_THRESHOLD, FLUENCY_NORMALIZE_DURATION, SPEED_STABILITY_THRESHOLD,
    SCORE_MULTIPLIER_EXCELLENT, SCORE_MULTIPLIER_GOOD, SCORE_MULTIPLIER_ACCEPTABLE, SCORE_MULTIPLIER_POOR,
    FLUENCY_MAX_SCORES
)
from app.constants.messages import (
    CRITERIA_NAME_FLUENCY,
    FEEDBACK_FLUENCY_EXCELLENT, FEEDBACK_FLUENCY_GOOD_TEMPLATE,
    FEEDBACK_FLUENCY_ACCEPTABLE_PREFIX, FEEDBACK_FLUENCY_POOR_PREFIX, FEEDBACK_FLUENCY_POOR_SUFFIX,
    ISSUE_SPEECH_TOO_SLOW, ISSUE_SPEECH_SLIGHTLY_SLOW, ISSUE_SPEECH_TOO_FAST, ISSUE_SPEECH_SLIGHTLY_FAST,
    ISSUE_TOO_MANY_PAUSES, ISSUE_PAUSES_TOO_LONG, ISSUE_HESITATION, ISSUE_SPEED_UNSTABLE,
    PROBLEM_WRONG_PAUSE, PROBLEM_HESITATION, PROBLEM_SPEED_UNSTABLE
)


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
            "speech_rate_slow": SPEECH_RATE_SLOW,
            "speech_rate_ideal_min": SPEECH_RATE_IDEAL_MIN,
            "speech_rate_ideal_max": SPEECH_RATE_IDEAL_MAX,
            "speech_rate_fast": SPEECH_RATE_FAST,
            "pause_ratio_excellent": PAUSE_RATIO_EXCELLENT,
            "pause_ratio_acceptable": PAUSE_RATIO_ACCEPTABLE,
            "pause_ratio_poor": PAUSE_RATIO_POOR,
            "mean_pause_excellent": MEAN_PAUSE_EXCELLENT,
            "mean_pause_acceptable": MEAN_PAUSE_ACCEPTABLE,
            "num_pauses_threshold": NUM_PAUSES_THRESHOLD
        }
        
        # Max score varies by exam level and task
        self.max_scores = FLUENCY_MAX_SCORES
    
    def get_criteria_name(self) -> str:
        return CRITERIA_NAME_FLUENCY
    
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
        normalized_pauses = (num_pauses / duration) * FLUENCY_NORMALIZE_DURATION if duration > 0 else num_pauses
        
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
        if speed_diff > SPEED_STABILITY_THRESHOLD:
            issues.append(ISSUE_SPEED_UNSTABLE)
            detected_problems.append(PROBLEM_SPEED_UNSTABLE)
        
        # Calculate score based on issues
        if not issues:
            score = max_score
            level = ScoreLevel.EXCELLENT
        elif len(issues) == 1:
            score = max_score * SCORE_MULTIPLIER_GOOD
            level = ScoreLevel.GOOD
        elif len(issues) == 2:
            score = max_score * SCORE_MULTIPLIER_ACCEPTABLE
            level = ScoreLevel.ACCEPTABLE
        else:
            score = max_score * SCORE_MULTIPLIER_POOR
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
            return ISSUE_SPEECH_TOO_SLOW
        elif rate < self.thresholds["speech_rate_ideal_min"]:
            return ISSUE_SPEECH_SLIGHTLY_SLOW
        elif rate > self.thresholds["speech_rate_fast"]:
            return ISSUE_SPEECH_TOO_FAST
        elif rate > self.thresholds["speech_rate_ideal_max"]:
            return ISSUE_SPEECH_SLIGHTLY_FAST
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
            issues.append(ISSUE_TOO_MANY_PAUSES)
            problems.append(PROBLEM_WRONG_PAUSE)
        elif mean_pause > self.thresholds["mean_pause_acceptable"]:
            issues.append(ISSUE_PAUSES_TOO_LONG)
            problems.append(PROBLEM_WRONG_PAUSE)
        
        # Hesitation (many short pauses)
        if normalized_pauses > self.thresholds["num_pauses_threshold"] and mean_pause < HESITATION_PAUSE_THRESHOLD:
            issues.append(ISSUE_HESITATION)
            problems.append(PROBLEM_HESITATION)
        
        return {"issues": issues, "problems": problems}
    
    def _generate_feedback(self, level: ScoreLevel, issues: List[str]) -> str:
        """Generate Vietnamese feedback based on scoring results"""
        
        if level == ScoreLevel.EXCELLENT:
            return FEEDBACK_FLUENCY_EXCELLENT
        elif level == ScoreLevel.GOOD:
            return FEEDBACK_FLUENCY_GOOD_TEMPLATE.format(issue=issues[0] if issues else '')
        elif level == ScoreLevel.ACCEPTABLE:
            feedback = FEEDBACK_FLUENCY_ACCEPTABLE_PREFIX
            feedback += "; ".join(issues[:2])
            return feedback
        else:
            feedback = FEEDBACK_FLUENCY_POOR_PREFIX
            feedback += FEEDBACK_FLUENCY_POOR_SUFFIX + "; ".join(issues)
            return feedback
