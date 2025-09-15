"""
Data models for conversation analysis
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum

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

class FailureCategory(Enum):
    """Categories of conversation failures"""
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    PERSONA_DRIFT = "persona_drift"
    SUT_ERROR = "sut_error"
    PROXY_ERROR = "proxy_error"
    PROTOCOL_VIOLATION = "protocol_violation"
    INCOMPLETE_INFORMATION = "incomplete_information"
    USER_ABANDONMENT = "user_abandonment"
    SYSTEM_ERROR = "system_error"
    VALIDATION_ERROR = "validation_error"

class ConversationStatus(Enum):
    """Status of conversation completion"""
    COMPLETED_SUCCESSFULLY = "completed_successfully"
    SUMMARY_PROVIDED_AWAITING_CONFIRMATION = "summary_provided_awaiting_confirmation"
    INCOMPLETE = "incomplete"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"

@dataclass
class FailureDetail:
    """Detailed information about a failure"""
    category: FailureCategory
    reason: str
    error_message: Optional[str] = None
    turn_occurred: Optional[int] = None
    context: Optional[Dict[str, Any]] = None

@dataclass
class ConversationOutcome:
    """Final outcome of the conversation"""
    status: ConversationStatus
    completion_level: int  # 0-100
    success_indicators: List[str]
    issues: List[str]
    failures: List[FailureDetail] = None
    total_failures: int = 0
    
    def __post_init__(self):
        """Initialize list fields if they are None"""
        if self.failures is None:
            self.failures = []
        self.total_failures = len(self.failures)

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
