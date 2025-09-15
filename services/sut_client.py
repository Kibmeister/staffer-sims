"""
SUT (System Under Test) Client
Handles communication with the Staffer chat endpoint
"""
import logging
from typing import List, Dict, Any
from .base_api_client import BaseAPIClient, APIClientConfig

logger = logging.getLogger(__name__)

class SUTClient(BaseAPIClient):
    """Client for interacting with the Staffer SUT endpoint"""
    
    def __init__(self, config: APIClientConfig):
        super().__init__(config)
        logger.info(f"SUT Client initialized for: {config.url}")
    
    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        """Extract content from SUT API response"""
        # Try OpenAI format first (for when SUT uses OpenAI API)
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0]["message"]["content"]
            logger.debug("Extracted content from OpenAI format")
            return content
        
        # Try direct message format (for custom SUT API)
        if "message" in response_data:
            content = response_data["message"]
            logger.debug("Extracted content from direct message format")
            return content
        
        logger.error(f"SUT response missing expected keys: {response_data}")
        raise ValueError("SUT response missing 'message' or 'choices[0][\"message\"][\"content\"]' key")
    
    def send_conversation(self, messages: List[Dict[str, str]], temperature: float | None = None, top_p: float | None = None) -> tuple[str, Dict[str, Any]]:
        """
        Send conversation to SUT endpoint
        
        Args:
            messages: List of conversation messages in OpenAI format
            
        Returns:
            Tuple of (SUT response content, usage data)
        """
        # Prepare payload for SUT endpoint
        payload = {"messages": messages}
        
        # Add model if configured (for OpenRouter/OpenAI APIs)
        if self.config.model:
            payload["model"] = self.config.model
        # Optional sampling controls; CLI/env overrides take precedence
        if temperature is None:
            temperature = self._get_temperature_default()
        if top_p is None:
            top_p = self._get_top_p_default()
        payload["temperature"] = float(temperature)
        payload["top_p"] = float(top_p)
        
        logger.info(f"Sending conversation to SUT with {len(messages)} messages")
        logger.debug(f"SUT payload: {payload}")
        
        try:
            response, usage = self.send_message(payload)
            logger.info(f"SUT response received (length: {len(response)}, tokens: {usage['total_tokens']})")
            return response, usage
        except Exception as e:
            logger.error(f"SUT request failed: {e}")
            raise
    
    def send_with_system_prompt(self, messages: List[Dict[str, str]], system_prompt: str, temperature: float | None = None, top_p: float | None = None) -> tuple[str, Dict[str, Any]]:
        """
        Send conversation with system prompt to SUT
        
        Args:
            messages: List of conversation messages
            system_prompt: System prompt to prepend
            
        Returns:
            Tuple of (SUT response content, usage data)
        """
        # Prepend system prompt to messages
        messages_with_system = [
            {"role": "system", "content": system_prompt}
        ] + messages
        
        return self.send_conversation(messages_with_system, temperature=temperature, top_p=top_p)

    def _get_temperature_default(self) -> float:
        # Pull from env-driven settings if present via headers; fallback default 0.7
        try:
            from config.settings import get_settings
            return float(get_settings().temperature)
        except Exception:
            return 0.7

    def _get_top_p_default(self) -> float:
        try:
            from config.settings import get_settings
            return float(get_settings().top_p)
        except Exception:
            return 1.0
