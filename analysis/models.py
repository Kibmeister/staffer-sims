"""
Data models for conversation analysis
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class ConversationTurn:
    """Represents a single turn in the conversation"""
    turn: int
    role: str
    content: str
    content_preview: str

@dataclass
class ConversationSummary:
    """Summary of the conversation flow and quality"""
    total_turns: int
    conversation_flow: List[ConversationTurn]
    key_information_gathered: List[str]
    conversation_quality: str = "unknown"

@dataclass
class ConversationOutcome:
    """Final outcome of the conversation"""
    status: str  # "completed_successfully", "summary_provided_awaiting_confirmation", "incomplete"
    completion_level: int  # 0-100
    success_indicators: List[str]
    issues: List[str]

@dataclass
class InformationGathered:
    """Structured information extracted from the conversation"""
    role_type: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    salary_range: Optional[str] = None
    skills_mentioned: List[str] = None
    responsibilities: List[str] = None
    deadline: Optional[str] = None
    
    def __post_init__(self):
        """Initialize list fields if they are None"""
        if self.skills_mentioned is None:
            self.skills_mentioned = []
        if self.responsibilities is None:
            self.responsibilities = []
