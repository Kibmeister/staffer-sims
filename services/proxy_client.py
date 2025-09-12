"""
Proxy Client
Handles communication with the proxy API (OpenAI/OpenRouter) for persona role-playing
"""
import logging
from typing import List, Dict, Any
from .base_api_client import BaseAPIClient, APIClientConfig

logger = logging.getLogger(__name__)

class ProxyClient(BaseAPIClient):
    """Client for interacting with proxy API for persona simulation"""
    
    def __init__(self, config: APIClientConfig):
        super().__init__(config)
        logger.info(f"Proxy Client initialized for: {config.url}")
    
    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        """Extract content from proxy API response"""
        # Proxy APIs should always use OpenAI format
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0]["message"]["content"]
            logger.debug("Extracted content from proxy API response")
            return content
        
        logger.error(f"Proxy API response missing expected format: {response_data}")
        raise ValueError("Proxy API response missing 'choices[0][\"message\"][\"content\"]' key")
    
    def _build_persona_system_prompt(self, persona: Dict[str, Any], scenario: Dict[str, Any]) -> str:
        """
        Build comprehensive system prompt for persona role-playing
        
        Args:
            persona: Persona configuration
            scenario: Scenario configuration
            
        Returns:
            Complete system prompt string
        """
        system_parts = []
        
        # Persona role adherence
        if persona.get('role_adherence'):
            system_parts.append(persona['role_adherence'])
        
        # Forbidden behaviors
        forbidden = persona.get('forbidden_behaviors', [])
        if forbidden:
            system_parts.append("FORBIDDEN BEHAVIORS:")
            system_parts.extend(forbidden)
        
        # Required behaviors
        required = persona.get('required_behaviors', [])
        if required:
            system_parts.append("REQUIRED BEHAVIORS:")
            system_parts.extend(required)
        
        # Response formula
        if persona.get('response_formula'):
            system_parts.append(f"RESPONSE FORMULA: {persona['response_formula']}")
        
        # Recovery phrase
        if persona.get('recovery_phrase'):
            system_parts.append(f"RECOVERY PHRASE: {persona['recovery_phrase']}")
        
        # Character motivation
        if persona.get('character_motivation'):
            system_parts.append(f"CHARACTER MOTIVATION: {persona['character_motivation']}")
        
        # Scenario-specific instructions
        if scenario.get('role_adherence'):
            system_parts.append(scenario['role_adherence'])
        
        # Scenario forbidden behaviors
        scenario_forbidden = scenario.get('forbidden_behaviors', [])
        if scenario_forbidden:
            system_parts.append("FORBIDDEN BEHAVIORS (scenario):")
            system_parts.extend(scenario_forbidden)
        
        # Scenario required behaviors
        scenario_required = scenario.get('required_behaviors', [])
        if scenario_required:
            system_parts.append("REQUIRED BEHAVIORS (scenario):")
            system_parts.extend(scenario_required)
        
        # Scenario response formula
        if scenario.get('response_formula'):
            system_parts.append(f"RESPONSE FORMULA (scenario): {scenario['response_formula']}")
        
        # Scenario recovery phrase
        if scenario.get('recovery_phrase'):
            system_parts.append(f"RECOVERY PHRASE (scenario): {scenario['recovery_phrase']}")
        
        # Scenario character motivation
        if scenario.get('character_motivation'):
            system_parts.append(f"CHARACTER MOTIVATION (scenario): {scenario['character_motivation']}")
        
        return "\n".join(system_parts)
    
    def send_persona_message(self, persona: Dict[str, Any], scenario: Dict[str, Any], 
                           messages: List[Dict[str, str]]) -> str:
        """
        Send persona message through proxy API
        
        Args:
            persona: Persona configuration
            scenario: Scenario configuration
            messages: Conversation messages
            
        Returns:
            Persona response content
        """
        # Build system prompt
        system_prompt = self._build_persona_system_prompt(persona, scenario)
        
        # Prepare payload for proxy API
        payload = {
            "model": self.config.model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt}
            ] + messages
        }
        
        logger.info(f"Sending persona message through proxy API with {len(messages)} messages")
        logger.debug(f"System prompt length: {len(system_prompt)}")
        logger.debug(f"Proxy payload keys: {list(payload.keys())}")
        
        try:
            response = self.send_message(payload)
            logger.info(f"Persona response received (length: {len(response)})")
            return response
        except Exception as e:
            logger.error(f"Proxy request failed: {e}")
            raise
