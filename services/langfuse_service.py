"""
Langfuse Service
Handles all Langfuse integrations including tracing, evaluations, and metadata management
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from langfuse import Langfuse

logger = logging.getLogger(__name__)

@dataclass
class LangfuseConfig:
    """Configuration for Langfuse service"""
    public_key: str
    secret_key: str
    host: Optional[str] = None

@dataclass
class ConversationMetadata:
    """Metadata for conversation tracking"""
    persona_name: str
    scenario_title: str
    total_turns: int
    completion_status: str
    completion_level: int
    transcript_path: str
    jsonl_path: str
    random_seed: Optional[str] = None
    temperature: Optional[str] = None
    top_p: Optional[str] = None

class LangfuseService:
    """Service for managing Langfuse integrations"""
    
    def __init__(self, config: LangfuseConfig):
        self.config = config
        self.client = self._initialize_client()
        logger.info(f"Langfuse service initialized with host: {config.host or 'default'}")
    
    def _initialize_client(self) -> Langfuse:
        """Initialize Langfuse client"""
        try:
            client = Langfuse(
                public_key=self.config.public_key,
                secret_key=self.config.secret_key,
                host=self.config.host
            )
            logger.debug("Langfuse client initialized successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse client: {e}")
            raise
    
    def start_conversation_trace(self, persona_name: str, scenario_title: str, 
                               entry_context: str) -> Any:
        """
        Start a new conversation trace
        
        Args:
            persona_name: Name of the persona
            scenario_title: Title of the scenario
            entry_context: Entry context for the conversation
            
        Returns:
            Langfuse trace context manager
        """
        logger.info(f"Starting conversation trace for {persona_name} - {scenario_title}")
        
        return self.client.start_as_current_observation(
            as_type='span',
            name="persona_simulation",
            input={
                "persona": persona_name,
                "scenario": scenario_title
            },
            metadata={
                "role": persona_name,
                "entry": entry_context
            }
        )
    
    def update_trace_tags(self, tags: List[str]) -> None:
        """Update current trace with tags"""
        try:
            self.client.update_current_trace(tags=tags)
            logger.debug(f"Updated trace tags: {tags}")
        except Exception as e:
            logger.warning(f"Failed to update trace tags: {e}")
    
    def start_sut_span(self, turn_idx: int, messages: List[Dict[str, str]]) -> Any:
        """
        Start a SUT message span
        
        Args:
            turn_idx: Current turn index
            messages: Messages being sent to SUT
            
        Returns:
            Langfuse span context manager
        """
        logger.debug(f"Starting SUT span for turn {turn_idx}")
        
        return self.client.start_as_current_observation(
            as_type='span',
            name="sut_message",
            input={"messages": messages},
            metadata={
                "turn": turn_idx,
                "activity": "sut_message",
                "model": "staffer-sut"
            }
        )
    
    def start_proxy_span(self, turn_idx: int, system_prompt: str, 
                        messages: List[Dict[str, str]]) -> Any:
        """
        Start a proxy message span
        
        Args:
            turn_idx: Current turn index
            system_prompt: System prompt being used
            messages: Messages being sent to proxy
            
        Returns:
            Langfuse span context manager
        """
        logger.debug(f"Starting proxy span for turn {turn_idx}")
        
        proxy_input = {
            "system": system_prompt,
            "messages": messages
        }
        
        return self.client.start_as_current_observation(
            as_type='span',
            name="proxy_message",
            input=proxy_input,
            metadata={
                "turn": turn_idx,
                "activity": "proxy_message",
                "system_prompt": system_prompt,
                "model": "gpt-4"
            }
        )
    
    def update_trace_output(self, conversation_summary: Dict[str, Any], 
                          final_outcome: Dict[str, Any], information_gathered: Dict[str, Any],
                          transcript: str, metadata: ConversationMetadata) -> None:
        """
        Update trace with final output and metadata
        
        Args:
            conversation_summary: Summary of the conversation
            final_outcome: Final outcome analysis
            information_gathered: Information extracted from conversation
            transcript: Full conversation transcript
            metadata: Conversation metadata
        """
        try:
            self.client.update_current_trace(
                output={
                    "conversation_summary": conversation_summary,
                    "final_outcome": final_outcome,
                    "total_turns": metadata.total_turns,
                    "information_gathered": information_gathered,
                    "transcript": transcript,
                    "persona": metadata.persona_name,
                    "scenario": metadata.scenario_title
                },
                metadata={
                    "transcript_path": metadata.transcript_path,
                    "jsonl_path": metadata.jsonl_path,
                    "completion_status": metadata.completion_status,
                    "completion_level": metadata.completion_level
                }
            )
            logger.info("Updated trace with final output and metadata")
        except Exception as e:
            logger.error(f"Failed to update trace output: {e}")
    
    def create_evaluation_event(self, transcript: str, turns_count: int, 
                              persona_name: str, scenario_title: str,
                              conversation_summary: Dict[str, Any],
                              final_outcome: Dict[str, Any],
                              information_gathered: Dict[str, Any]) -> None:
        """
        Create evaluation event for Langfuse
        
        Args:
            transcript: Full conversation transcript
            turns_count: Number of conversation turns
            persona_name: Name of the persona
            scenario_title: Title of the scenario
            conversation_summary: Summary of the conversation
            final_outcome: Final outcome analysis
            information_gathered: Information extracted from conversation
        """
        try:
            self.client.create_event(
                name="conversation_evaluation",
                input=transcript,
                output={
                    "transcript": transcript,
                    "turns": turns_count,
                    "persona": persona_name,
                    "scenario": scenario_title,
                    "conversation_summary": conversation_summary,
                    "final_outcome": final_outcome,
                    "information_gathered": information_gathered
                }
            )
            logger.info("Created evaluation event")
        except Exception as e:
            logger.error(f"Failed to create evaluation event: {e}")
    
    def flush(self) -> None:
        """Flush all pending data to Langfuse"""
        try:
            self.client.flush()
            logger.debug("Flushed data to Langfuse")
        except Exception as e:
            logger.error(f"Failed to flush data to Langfuse: {e}")
