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
            for behavior in forbidden:
                system_parts.append(f"- {behavior}")
        
        # Required behaviors
        required = persona.get('required_behaviors', [])
        if required:
            system_parts.append("REQUIRED BEHAVIORS:")
            for behavior in required:
                system_parts.append(f"- {behavior}")
        
        # Response formula
        if persona.get('response_formula'):
            system_parts.append(f"RESPONSE FORMULA: {persona['response_formula']}")
            # If persona demands single-sentence replies, add an explicit hard limit
            if '1 sentence' in persona['response_formula'].lower() or 'one sentence' in persona['response_formula'].lower():
                system_parts.append("HARD LIMIT: Your replies MUST be a single sentence only. No multi-part answers.")
        
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
            for behavior in scenario_forbidden:
                system_parts.append(f"- {behavior}")
        
        # Scenario required behaviors
        scenario_required = scenario.get('required_behaviors', [])
        if scenario_required:
            system_parts.append("REQUIRED BEHAVIORS (scenario):")
            for behavior in scenario_required:
                system_parts.append(f"- {behavior}")
        
        # Scenario response formula (only if persona hasn't defined one to avoid conflicts)
        if scenario.get('response_formula') and not persona.get('response_formula'):
            system_parts.append(f"RESPONSE FORMULA (scenario): {scenario['response_formula']}")
        
        # Scenario recovery phrase — suppress if persona already defines one
        if scenario.get('recovery_phrase') and not persona.get('recovery_phrase'):
            system_parts.append(f"RECOVERY PHRASE (scenario): {scenario['recovery_phrase']}")
        
        # Scenario character motivation
        if scenario.get('character_motivation'):
            system_parts.append(f"CHARACTER MOTIVATION (scenario): {scenario['character_motivation']}")

        # Scenario grounding: title and entry context to avoid drift
        title = scenario.get('title')
        entry = scenario.get('entry_context')
        if title or entry:
            system_parts.append("SCENARIO CONTEXT (for grounding, do not repeat verbatim):")
            if title:
                system_parts.append(f"- Title: {title}")
            if entry:
                system_parts.append(f"- Entry context: {entry.strip()}")
            # Explicit constraint to prevent role drift
            system_parts.append(
                "Respond in one natural sentence. Align with the scenario context; do not invent a different role title."
            )
            system_parts.append(
                "If greeted with 'How can I help you?', state your hiring need from the entry context succinctly."
            )
            system_parts.append(
                "Never mirror or repeat the assistant's question verbatim; answer directly and concisely."
            )

        # Interaction contract: engine-computed runtime rules and dials
        contract = scenario.get('interaction_contract')
        if contract:
            system_parts.append(contract)

        # Turn controller: per-turn gates (clarifying/tangent/cooldown/closure)
        turn_controller = scenario.get('turn_controller')
        if turn_controller:
            system_parts.append(turn_controller)
        
        return "\n".join(system_parts)
    
    def send_persona_message(self, persona: Dict[str, Any], scenario: Dict[str, Any], 
                           messages: List[Dict[str, str]]) -> tuple[str, Dict[str, Any]]:
        """
        Send persona message through proxy API
        
        Args:
            persona: Persona configuration
            scenario: Scenario configuration
            messages: Conversation messages
            
        Returns:
            Tuple of (Persona response content, usage data)
        """
        # Build system prompt from persona and scenario only
        system_prompt = self._build_persona_system_prompt(persona, scenario)
        
        # Defense-in-depth: ensure we only send ONE system message total
        cleaned_messages = [m for m in messages if m.get("role") != "system"]
        
        # Capture last assistant message for anti-echo sanitization
        last_assistant = None
        for m in reversed(cleaned_messages):
            if m.get("role") == "assistant":
                last_assistant = (m.get("content") or "").strip()
                break
        
        # Prepare payload for proxy API
        payload = {
            "model": self.config.model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt}
            ] + cleaned_messages
        }

        # Sampling controls (temperature/top_p): prefer scenario overrides, then settings/env
        try:
            temp_override = scenario.get('temperature_override')
            top_p_override = scenario.get('top_p_override')
            if temp_override is not None:
                payload["temperature"] = float(temp_override)
            if top_p_override is not None:
                payload["top_p"] = float(top_p_override)
            if temp_override is None or top_p_override is None:
                from config.settings import get_settings
                settings = get_settings()
                if temp_override is None:
                    payload["temperature"] = settings.temperature
                if top_p_override is None:
                    payload["top_p"] = settings.top_p
        except Exception:
            pass
        
        logger.info(f"Sending persona message through proxy API with {len(messages)} messages")
        logger.debug(f"System prompt length: {len(system_prompt)}")
        logger.debug(f"Proxy payload keys: {list(payload.keys())}")
        
        try:
            response, usage = self.send_message(payload)
            logger.info(f"Persona response received (length: {len(response)}, tokens: {usage['total_tokens']})")
            return response, usage
        except Exception as e:
            logger.error(f"Proxy request failed: {e}")
            raise


    def _enforce_single_sentence(self, text: str) -> str:
        """Trim reply to a single sentence for brevity and consistency."""
        s = text.strip()
        if not s:
            return s
        # Find first terminal punctuation. Prefer '?', '!' or '.'
        first_q = s.find('?') if '?' in s else -1
        first_e = s.find('!') if '!' in s else -1
        first_p = s.find('.') if '.' in s else -1

        candidates = [idx for idx in [first_q, first_e, first_p] if idx != -1]
        if not candidates:
            # No clear sentence boundary; return as-is but cap length
            return s[:240]
        end = min(candidates)
        single = s[: end + 1].strip()
        return single
