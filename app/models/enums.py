"""
Enums for HSKK Scoring System
"""
from enum import Enum


class HSKKLevel(str, Enum):
    """HSKK proficiency levels"""
    ELEMENTARY = "elementary"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
