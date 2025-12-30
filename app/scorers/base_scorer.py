"""
Base Scorer - Abstract base class for all scoring implementations
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ScoreLevel(Enum):
    """Score quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"


@dataclass
class ScoringResult:
    """Result from a scorer"""
    score: float
    max_score: float
    level: ScoreLevel
    issues: List[str] = field(default_factory=list)
    feedback: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def percentage(self) -> float:
        """Score as percentage"""
        if self.max_score == 0:
            return 0.0
        return (self.score / self.max_score) * 100


class BaseScorer(ABC):
    """Abstract base class for all scorers"""
    
    def __init__(self, exam_level: str = "beginner"):
        """
        Initialize scorer
        
        Args:
            exam_level: "beginner", "intermediate", or "advanced"
        """
        self.exam_level = exam_level
        self._load_thresholds()
    
    @abstractmethod
    def _load_thresholds(self) -> None:
        """Load scoring thresholds based on exam level"""
        pass
    
    @abstractmethod
    def score(self, data: Dict[str, Any]) -> ScoringResult:
        """
        Calculate score based on input data
        
        Args:
            data: Input data for scoring
            
        Returns:
            ScoringResult with score, level, issues, and feedback
        """
        pass
    
    @abstractmethod
    def get_criteria_name(self) -> str:
        """Return the name of scoring criteria"""
        pass
    
    def _determine_level(self, score: float, max_score: float) -> ScoreLevel:
        """Determine score level based on percentage"""
        if max_score == 0:
            return ScoreLevel.POOR
        
        pct = (score / max_score) * 100
        
        if pct >= 90:
            return ScoreLevel.EXCELLENT
        elif pct >= 70:
            return ScoreLevel.GOOD
        elif pct >= 50:
            return ScoreLevel.ACCEPTABLE
        else:
            return ScoreLevel.POOR
