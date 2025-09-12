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
    
    def send_conversation(self, messages: List[Dict[str, str]]) -> str:
        """
        Send conversation to SUT endpoint
        
        Args:
            messages: List of conversation messages in OpenAI format
            
        Returns:
            SUT response content
        """
        # Prepare payload for SUT endpoint
        payload = {"messages": messages}
        
        # Add model if configured (for OpenRouter/OpenAI APIs)
        if self.config.model:
            payload["model"] = self.config.model
        
        logger.info(f"Sending conversation to SUT with {len(messages)} messages")
        logger.debug(f"SUT payload: {payload}")
        
        try:
            response = self.send_message(payload)
            logger.info(f"SUT response received (length: {len(response)})")
            return response
        except Exception as e:
            logger.error(f"SUT request failed: {e}")
            raise
    
    def send_with_system_prompt(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        """
        Send conversation with system prompt to SUT
        
        Args:
            messages: List of conversation messages
            system_prompt: System prompt to prepend
            
        Returns:
            SUT response content
        """
        # Prepend system prompt to messages
        messages_with_system = [
            {"role": "system", "content": system_prompt}
        ] + messages
        
        return self.send_conversation(messages_with_system)
