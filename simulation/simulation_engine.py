"""
Simulation Engine
Main orchestrator for persona simulation conversations
"""
import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from services import SUTClient, ProxyClient, LangfuseService
from services.base_api_client import APIClientConfig
from services.langfuse_service import LangfuseConfig, ConversationMetadata
from analysis import ConversationAnalyzer
from config.settings import Settings

logger = logging.getLogger(__name__)

class SimulationEngine:
    """Main engine for running persona simulations"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.analyzer = ConversationAnalyzer()
        
        # Initialize clients
        self.sut_client = self._create_sut_client()
        self.proxy_client = self._create_proxy_client()
        self.langfuse_service = self._create_langfuse_service()
        
        logger.info("Simulation engine initialized")
    
    def _create_sut_client(self) -> SUTClient:
        """Create SUT client from settings"""
        sut_config = self.settings.get_sut_api_config()
        config = APIClientConfig(
            url=sut_config["url"],
            headers=sut_config["headers"],
            timeout=self.settings.request_timeout,
            max_retries=self.settings.retry_attempts,
            model=sut_config.get("model")
        )
        return SUTClient(config)
    
    def _create_proxy_client(self) -> ProxyClient:
        """Create proxy client from settings"""
        proxy_config = self.settings.get_proxy_api_config()
        config = APIClientConfig(
            url=proxy_config["url"],
            headers=proxy_config["headers"],
            timeout=self.settings.request_timeout,
            max_retries=self.settings.retry_attempts,
            model=proxy_config.get("model")
        )
        return ProxyClient(config)
    
    def _create_langfuse_service(self) -> LangfuseService:
        """Create Langfuse service from settings"""
        lf_config = self.settings.get_langfuse_config()
        config = LangfuseConfig(
            public_key=lf_config["public_key"],
            secret_key=lf_config["secret_key"],
            host=lf_config.get("host")
        )
        return LangfuseService(config)
    
    def _build_persona_system_prompt(self, persona: Dict[str, Any]) -> str:
        """Build system prompt for persona role-playing"""
        return (
            f"You role-play {persona['name']}, a {persona['role']}. "
            f"Style: {persona.get('voice','concise')}. "
            f"Goals: {', '.join(persona.get('goals', [])).strip()}. "
            "Provide multiple details in one message when asked for basics. "
            "If unsure, ask 1 clarifying question; otherwise answer naturally."
        )
    
    def _save_transcript(self, run_id: str, persona: Dict[str, Any], 
                        scenario: Dict[str, Any], turns: List[Dict[str, Any]], 
                        output_dir: str) -> tuple[str, str]:
        """
        Save conversation transcript in both markdown and JSONL formats
        
        Returns:
            Tuple of (markdown_path, jsonl_path)
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Build safe filename parts including persona and scenario
        def _slugify(value: str) -> str:
            value = value.strip().lower()
            value = re.sub(r"[\s]+", "-", value)
            value = re.sub(r"[^a-z0-9_-]", "", value)
            return value

        persona_slug = _slugify(str(persona.get("name", "persona")))
        scenario_slug = _slugify(str(scenario.get("title", "scenario")))
        base_name = f"{run_id}__{persona_slug}__{scenario_slug}"

        # Save markdown
        md_path = os.path.join(output_dir, f"{base_name}.md")
        with open(md_path, "w") as f:
            f.write(self._to_markdown(run_id, persona, scenario, turns))
        
        # Save JSONL
        jsonl_path = os.path.join(output_dir, f"{base_name}.jsonl")
        with open(jsonl_path, "w") as f:
            for turn in turns:
                f.write(json.dumps(turn, ensure_ascii=False) + "\n")
        
        logger.info(f"Saved transcript: {md_path} and {jsonl_path}")
        return md_path, jsonl_path
    
    def _to_markdown(self, run_id: str, persona: Dict[str, Any], 
                    scenario: Dict[str, Any], turns: List[Dict[str, Any]]) -> str:
        """Convert conversation to markdown format"""
        lines = [
            f"# Transcript {run_id}",
            f"**Persona:** {persona['name']}",
            f"**Scenario:** {scenario['title']}",
            ""
        ]
        
        for turn in turns:
            lines.append(f"**{turn['role'].title()}**: {turn['content']}")
        
        return "\n\n".join(lines)
    
    def run_simulation(self, persona: Dict[str, Any], scenario: Dict[str, Any], 
                      output_dir: str = None) -> Dict[str, Any]:
        """
        Run a complete persona simulation
        
        Args:
            persona: Persona configuration
            scenario: Scenario configuration
            output_dir: Output directory for transcripts
            
        Returns:
            Simulation results dictionary
        """
        run_id = self._generate_run_id()
        max_turns = scenario.get("max_turns", self.settings.max_turns)
        output_dir = output_dir or self.settings.output_dir
        
        logger.info(f"Starting simulation {run_id} with {max_turns} max turns")
        
        # Compute and attach run-time behavior dials and interaction contract
        dials, seed = self._compute_runtime_dials(persona, scenario)
        scenario = dict(scenario)
        scenario["interaction_contract"] = self._build_interaction_contract(persona, scenario, dials, seed)

        # Initialize conversation - start with empty messages; SUT will make first message
        messages = []
        turns = []
        persona_system_prompt = self._build_persona_system_prompt(persona)
        
        # Start Langfuse trace
        with self.langfuse_service.start_conversation_trace(
            persona["name"], scenario["title"], scenario.get("entry_context", "")
        ) as trace:
            
            # Set trace tags
            self.langfuse_service.update_trace_tags([
                persona["name"], 
                scenario["title"],
                f"seed:{seed}",
                f"clarify:{dials['clarifying_question_prob']:.2f}",
                f"tangent:{dials['tangent_prob_after_field']:.2f}",
                f"hesitation:{dials['hesitation_insert_prob']:.2f}"
            ])
            
            # Main conversation loop
            sut_provided_summary = False
            
            for turn_idx in range(max_turns):
                logger.debug(f"Starting turn {turn_idx + 1}")
                
                # SUT turn: Generate SUT response
                sut_reply = self._handle_sut_turn(turn_idx, messages, persona_system_prompt)
                turns.append({"role": "system", "content": sut_reply})
                messages.append({"role": "assistant", "content": sut_reply})
                
                # Check if SUT provided summary
                sut_provided_summary = self.analyzer.check_sut_provided_summary(sut_reply)
                if sut_provided_summary:
                    logger.info(f"SUT provided summary at turn {turn_idx + 1}")
                
                # Proxy turn: Generate proxy response  
                proxy_reply = self._handle_proxy_turn(turn_idx, messages, sut_reply,
                                                    persona, scenario, persona_system_prompt)
                turns.append({"role": "user", "content": proxy_reply})
                messages.append({"role": "user", "content": proxy_reply})
                
                # Check for conversation completion
                if sut_provided_summary and self.analyzer.check_proxy_confirmation(proxy_reply):
                    logger.info(f"Conversation completed successfully at turn {turn_idx + 1}")
                    break
            
            # Save transcript
            md_path, jsonl_path = self._save_transcript(run_id, persona, scenario, turns, output_dir)
            
            # Analyze conversation
            conversation_summary = self.analyzer.extract_conversation_summary(turns)
            
            # Check if proxy confirmed (look at last proxy response)
            proxy_confirmed = False
            if turns and turns[-1].get("role") == "user":
                proxy_confirmed = self.analyzer.check_proxy_confirmation(
                    turns[-1].get("content", "")
                )
            
            final_outcome = self.analyzer.determine_conversation_outcome(
                turns, sut_provided_summary, proxy_confirmed
            )
            information_gathered = self.analyzer.extract_information_gathered(turns)
            
            # Update Langfuse trace
            metadata = ConversationMetadata(
                persona_name=persona["name"],
                scenario_title=scenario["title"],
                total_turns=len(turns),
                completion_status=final_outcome.status,
                completion_level=final_outcome.completion_level,
                transcript_path=md_path,
                jsonl_path=jsonl_path
            )
            
            transcript_md = self._to_markdown(run_id, persona, scenario, turns)
            
            self.langfuse_service.update_trace_output(
                conversation_summary.__dict__, final_outcome.__dict__, 
                information_gathered.__dict__, transcript_md, metadata
            )
            
            # Create evaluation event
            self.langfuse_service.create_evaluation_event(
                transcript_md, len(turns), persona["name"], scenario["title"],
                conversation_summary.__dict__, final_outcome.__dict__, 
                information_gathered.__dict__
            )
            
            # Flush Langfuse data
            self.langfuse_service.flush()
            
            # Prepare results
            results = {
                "run_id": run_id,
                "persona": persona["name"],
                "scenario": scenario["title"],
                "total_turns": len(turns),
                "conversation_summary": conversation_summary.__dict__,
                "final_outcome": final_outcome.__dict__,
                "information_gathered": information_gathered.__dict__,
                "transcript_path": md_path,
                "jsonl_path": jsonl_path
            }
            
            logger.info(f"Simulation completed: {final_outcome.status} ({final_outcome.completion_level}%)")
            return results
    
    def _handle_sut_turn(self, turn_idx: int, messages: List[Dict[str, str]], 
                        system_prompt: str) -> str:
        """Handle a single SUT turn"""
        # For the first turn, use a special introductory prompt
        if turn_idx == 0:
            recruiter_prompt = self._load_intro_prompt()
            logger.debug(f"Using intro prompt for turn {turn_idx}")
        else:
            recruiter_prompt = self._load_recruiter_prompt()
            logger.debug(f"Using full recruiter prompt for turn {turn_idx}")
        
        # Prepend a lightweight controller to reduce multi-question drift
        recruiter_prompt = self._prepend_controller(recruiter_prompt)
        
        messages_for_sut = [
            {"role": "system", "content": recruiter_prompt}
        ] + messages
        
        with self.langfuse_service.start_sut_span(turn_idx, messages_for_sut) as sut_span:
            sut_reply = self.sut_client.send_conversation(messages_for_sut)
            # Enforce one-question-only where appropriate
            is_summary = self.analyzer.check_sut_provided_summary(sut_reply)
            if not is_summary:
                if turn_idx == 0:
                    sut_reply = self._enforce_single_question_first_turn(sut_reply)
                else:
                    sut_reply = self._enforce_single_question_all_turns(sut_reply)
            sut_span.update(output={"text": sut_reply})
            return sut_reply
    
    def _handle_proxy_turn(self, turn_idx: int, messages: List[Dict[str, str]], 
                          sut_reply: str, persona: Dict[str, Any], 
                          scenario: Dict[str, Any], system_prompt: str) -> str:
        """Handle a single proxy turn"""
        # Use existing conversation history; last message should already be the SUT reply
        messages_for_proxy = self._sanitize_messages_for_proxy(messages)
        
        # For the first turn, inject entry_context to ground the proxy properly
        if turn_idx == 0:
            entry_context = scenario.get('entry_context', '').strip()
            if entry_context:
                # Create a synthetic first message using entry_context
                messages_for_proxy = [{"role": "user", "content": entry_context}]
        
        with self.langfuse_service.start_proxy_span(turn_idx, system_prompt, messages_for_proxy) as proxy_span:
            proxy_reply = self.proxy_client.send_persona_message(
                persona, scenario, messages_for_proxy
            )
            proxy_span.update(output={"text": proxy_reply})
            return proxy_reply

    def _sanitize_messages_for_proxy(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Remove system-role messages; keep only assistant/user for the proxy."""
        return [m for m in messages if m.get("role") in {"assistant", "user"}]

    
    def _load_intro_prompt(self) -> str:
        """Load the introductory prompt for the first SUT message"""
        return """You are an expert recruiter assistant with extensive experience in hiring and recruiting. You help hiring managers define roles, clarify requirements, and streamline the hiring process.

Your capabilities include:
- Role definition and job description creation
- Candidate criteria development  
- Screening question creation
- Hiring process optimization

You are warm, professional, and efficient. You ask thoughtful questions to understand hiring needs and provide actionable guidance.

CRITICAL FIRST MESSAGE RULES:
- Use a brief greeting (one short sentence max).
- Ask EXACTLY ONE question. No multi-part or follow-up questions.
- The single question should be: "How can I help you?" (or a close variant).
- Do not assume any specific role, job title, or needs. Do not mention job titles.

Example (acceptable): "Hi — I’m your recruiter assistant. How can I help you?"

Do not add any second question in the same message.
"""

    def _enforce_single_question_first_turn(self, text: str) -> str:
        """Ensure the first SUT message contains at most one question.

        Keeps any brief greeting prior to the first question mark and truncates
        everything after the first '?'. If no question mark is present, return a
        minimal compliant message.
        """
        try:
            if not text:
                return "Hi — how can I help you?"
            qpos = text.find("?")
            if qpos == -1:
                # No question found; replace with compliant first turn
                return "Hi — how can I help you?"
            # Include content up to and including the first question mark
            trimmed = text[: qpos + 1].strip()
            # Guard against pathologically long greetings
            if len(trimmed) > 500:
                return "Hi — how can I help you?"
            return trimmed
        except Exception:
            return "Hi — how can I help you?"
    
    def _load_recruiter_prompt(self) -> str:
        """Load the recruiter system prompt from file"""
        try:
            prompt_path = Path("prompts/recruiter_v1.txt")
            if prompt_path.exists():
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logger.warning("Recruiter prompt file not found, using fallback")
                return "You are a recruiter assistant. Ask questions to understand the hiring needs and gather information progressively. Do not provide complete job descriptions immediately."
        except Exception as e:
            logger.error(f"Error loading recruiter prompt: {e}")
            return "You are a recruiter assistant. Ask questions to understand the hiring needs and gather information progressively. Do not provide complete job descriptions immediately."
    
    def _prepend_controller(self, prompt: str) -> str:
        """Add a compact controller to minimize instruction overload and enforce single-question behavior."""
        controller = (
            "DIALOG CONTROLLER (hard constraints):\n"
            "- Ask EXACTLY ONE question per turn.\n"
            "- Do not include more than one question mark in a message.\n"
            "- Keep the message short and avoid multi-part questions.\n"
            "- If you accidentally start forming a second question, stop and send only the first.\n"
        )
        return controller + "\n" + prompt
    
    def _generate_run_id(self) -> str:
        """Generate unique run ID"""
        import uuid
        # Use LOCAL time (24h) + day/month/year in a file-system safe format
        # Desired human format would be "HH:mm dd/MM/yyyy", but ":" and "/" are unsafe in filenames.
        # We therefore map to "HH-mm_dd-MM-yyyy" while preserving the same information.
        return datetime.now().strftime("%H-%M_%d-%m-%Y") + f"_run-{uuid.uuid4().hex[:6]}"

    def _enforce_single_question_all_turns(self, text: str) -> str:
        """Ensure SUT messages contain at most one question (general turns)."""
        try:
            if not text:
                return text
            # Count question marks; if more than one, trim after the first
            qpos = text.find("?")
            if qpos == -1:
                return text
            # If there is another question mark after the first, trim
            if text.find("?", qpos + 1) != -1:
                return text[: qpos + 1].strip()
            return text
        except Exception:
            return text

    # ------------------------------
    # Runtime dials & contract
    # ------------------------------
    def _compute_runtime_dials(self, persona: Dict[str, Any], scenario: Dict[str, Any]) -> tuple[Dict[str, float], int]:
        """Compute behavior dials per run using persona + scenario.

        Returns a tuple of (dials dict, randomness seed int).
        """
        import uuid

        def _val_or_default(container: Dict[str, Any], path: List[str], default: float) -> float:
            cur: Any = container
            try:
                for key in path:
                    cur = cur.get(key, {}) if isinstance(cur, dict) else {}
                return float(cur) if isinstance(cur, (int, float)) else default
            except Exception:
                return default

        # Pressure index mapping
        level_to_num = {"high": 1.0, "medium": 0.7, "low": 0.4}
        pi: Dict[str, Any] = scenario.get("pressure_index", {}) or {}
        if isinstance(pi, dict):
            vals: List[float] = [level_to_num.get(str(pi.get(k, "medium")).lower(), 0.7) for k in ["timeline", "quality", "budget"]]
            pressure_avg = sum(vals) / len(vals) if vals else 0.7
            budget_factor = level_to_num.get(str(pi.get("budget", "medium")).lower(), 0.7)
        else:
            pressure_avg = 0.7
            budget_factor = 0.7

        # Persona propensities
        question_uncertain = (
            persona.get("behavior_dials", {})
                   .get("question_propensity", {})
                   .get("when_uncertain", 0.6)
        )
        question_budget = (
            persona.get("behavior_dials", {})
                   .get("question_propensity", {})
                   .get("when_budget", 0.5)
        )
        tangent_after_field = (
            persona.get("behavior_dials", {})
                   .get("tangent_propensity", {})
                   .get("after_field_capture", 0.3)
        )
        elaboration_two = (
            persona.get("behavior_dials", {})
                   .get("elaboration_distribution", {})
                   .get("two_sentences", 0.25)
        )

        # Combine into runtime dials
        def clamp01(x: float) -> float:
            return max(0.0, min(1.0, x))

        clarifying_prob = clamp01(question_uncertain * pressure_avg * 1.0)
        # Slightly boost if budget pressure is high
        clarifying_prob = clamp01(clarifying_prob * (0.9 + 0.2 * budget_factor))

        tangent_prob = clamp01(tangent_after_field * min(1.0, pressure_avg))
        hesitation_prob = clamp01(float(elaboration_two))

        seed = int(uuid.uuid4().hex[:8], 16)

        dials = {
            "clarifying_question_prob": round(clarifying_prob, 3),
            "tangent_prob_after_field": round(tangent_prob, 3),
            "hesitation_insert_prob": round(hesitation_prob, 3)
        }
        return dials, seed

    def _build_interaction_contract(self, persona: Dict[str, Any], scenario: Dict[str, Any], dials: Dict[str, float], seed: int) -> str:
        """Create a compact interaction contract block for the proxy system prompt."""
        patterns = persona.get("behavior_dials", {}).get("hesitation_patterns", []) or []
        patterns_str = ", ".join([str(p) for p in patterns]) if patterns else "Hmm…, Honestly…, Let me think…"

        parts: List[str] = [
            "INTERACTION CONTRACT (engine-controlled):",
            "PRIORITIES:",
            "1) mandatory_fields (answer recruiter; provide the requested field)",
            "2) consultative_questions (only after fields are provided)",
            "3) tangent_handling (micro-detours max 1 every 3–4 turns; resume last question)",
            "4) closure_policy (when recruiter summarizes, confirm succinctly)",
            "BEHAVIOR DIALS:",
            f"- clarifying_question_prob: {dials['clarifying_question_prob']}",
            f"- tangent_prob_after_field: {dials['tangent_prob_after_field']}",
            f"- hesitation_insert_prob: {dials['hesitation_insert_prob']}",
            f"- randomness_seed: {seed}",
            f"HESITATION PATTERNS: {patterns_str}"
        ]
        return "\n".join(parts)
