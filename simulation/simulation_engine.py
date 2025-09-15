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
from dataclasses import dataclass

from services import SUTClient, ProxyClient, LangfuseService
from services.base_api_client import APIClientConfig
from services.langfuse_service import LangfuseConfig, ConversationMetadata
from analysis import ConversationAnalyzer
from analysis.models import ConversationStatus
from config.settings import Settings

logger = logging.getLogger(__name__)

@dataclass
class UsageStats:
    """Track API usage and costs"""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    sut_calls: int = 0
    proxy_calls: int = 0
    estimated_cost: float = 0.0

class SimulationEngine:
    """Main engine for running persona simulations"""
    
    def __init__(self, settings: Settings, sut_prompt_path: str = "prompts/recruiter_v1.txt"):
        self.settings = settings
        self.analyzer = ConversationAnalyzer()
        self.sut_prompt_path = sut_prompt_path
        
        # Initialize clients
        self.sut_client = self._create_sut_client()
        self.proxy_client = self._create_proxy_client()
        self.langfuse_service = self._create_langfuse_service()
        
        # Initialize usage tracking
        self.usage_stats = UsageStats()
        
        logger.info("Simulation engine initialized with connection pooling (pool_connections={}, pool_maxsize={})".format(
            self.settings.pool_connections, self.settings.pool_maxsize))
    
    def _create_sut_client(self) -> SUTClient:
        """Create SUT client from settings"""
        sut_config = self.settings.get_sut_api_config()
        config = APIClientConfig(
            url=sut_config["url"],
            headers=sut_config["headers"],
            timeout=self.settings.request_timeout,
            connection_timeout=10,  # 10 seconds for connection establishment
            max_retries=self.settings.retry_attempts,
            model=sut_config.get("model"),
            pool_connections=self.settings.pool_connections,
            pool_maxsize=self.settings.pool_maxsize,
            pool_block=False
        )
        return SUTClient(config)
    
    def _create_proxy_client(self) -> ProxyClient:
        """Create proxy client from settings"""
        proxy_config = self.settings.get_proxy_api_config()
        config = APIClientConfig(
            url=proxy_config["url"],
            headers=proxy_config["headers"],
            timeout=self.settings.request_timeout,
            connection_timeout=10,  # 10 seconds for connection establishment
            max_retries=self.settings.retry_attempts,
            model=proxy_config.get("model"),
            pool_connections=self.settings.pool_connections,
            pool_maxsize=self.settings.pool_maxsize,
            pool_block=False
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
                        output_dir: str, elapsed_time: float = 0, 
                        timeout_reached: bool = False, timeout_limit: int = 120) -> tuple[str, str]:
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

        # Save markdown (will be updated later with analysis)
        md_path = os.path.join(output_dir, f"{base_name}.md")
        
        # Save JSONL
        jsonl_path = os.path.join(output_dir, f"{base_name}.jsonl")
        with open(jsonl_path, "w") as f:
            for turn in turns:
                f.write(json.dumps(turn, ensure_ascii=False) + "\n")
        
        logger.info(f"Saved transcript: {md_path} and {jsonl_path}")
        return md_path, jsonl_path
    
    def _to_markdown(self, run_id: str, persona: Dict[str, Any], 
                    scenario: Dict[str, Any], turns: List[Dict[str, Any]], 
                    elapsed_time: float = 0, timeout_reached: bool = False, timeout_limit: int = 120,
                    final_outcome=None) -> str:
        """Convert conversation to markdown format with enhanced failure reporting"""
        lines = [
            f"# Transcript {run_id}",
            f"**Persona:** {persona['name']}",
            f"**Scenario:** {scenario['title']}",
            f"**SUT System Prompt:** {self.sut_prompt_path}"
        ]
        
        # Extract model and timestamp information for each role (SUT and Proxy)
        sut_model = None
        sut_timestamp = None
        proxy_model = None
        proxy_timestamp = None
        
        for turn in turns:
            if turn['role'] == 'system' and sut_model is None:
                sut_model = turn.get('model', 'unknown-model')
                sut_timestamp = turn.get('timestamp', 'unknown-time')
            elif turn['role'] == 'user' and proxy_model is None:
                proxy_model = turn.get('model', 'unknown-model')
                proxy_timestamp = turn.get('timestamp', 'unknown-time')
        
        # Add model and timestamp information under Scenario
        if sut_model and sut_timestamp:
            lines.append(f"**SUT Model:** {sut_model} - {sut_timestamp}")
        if proxy_model and proxy_timestamp:
            lines.append(f"**Proxy Model:** {proxy_model} - {proxy_timestamp}")
        
        # Add timeout information
        timeout_status = " (TIMEOUT REACHED)" if timeout_reached else ""
        lines.append(f"**Conversation Duration:** {elapsed_time:.1f}s / {timeout_limit}s{timeout_status}")
        
        # Add failure information if available
        if final_outcome and final_outcome.total_failures > 0:
            lines.append(f"**Failures Detected:** {final_outcome.total_failures}")
            lines.append("")
            lines.append("## 🚨 Failure Analysis")
            lines.append("")
            for failure in final_outcome.failures:
                turn_info = f" (Turn {failure.turn_occurred})" if failure.turn_occurred else ""
                lines.append(f"### {failure.category.value.replace('_', ' ').title()}{turn_info}")
                lines.append(f"**Reason:** {failure.reason}")
                if failure.error_message:
                    lines.append(f"**Error:** `{failure.error_message}`")
                if failure.context:
                    lines.append(f"**Context:** {failure.context}")
                lines.append("")
        
        lines.append("")
        
        # Add conversation turns with controller block if present
        for turn in turns:
            role = turn['role'].title()
            content = turn['content']
            controller = turn.get('turn_controller')
            if controller:
                lines.append(f"<details><summary>Controller</summary>\n\n{controller}\n</details>")
            lines.append(f"**{role}**: {content}")
        
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
        import time
        
        run_id = self._generate_run_id()
        max_turns = scenario.get("max_turns", self.settings.max_turns)
        output_dir = output_dir or self.settings.output_dir
        
        # Set timeout limit (120 seconds by default, configurable via scenario)
        timeout_seconds = scenario.get("conversation_timeout", 120)
        simulation_start_time = time.time()
        
        logger.info(f"Starting simulation {run_id} with {max_turns} max turns and {timeout_seconds}s timeout")
        
        # Compute and attach run-time behavior dials and interaction contract
        # Allow seed override from scenario (CLI/env)
        seed_override = scenario.get("rng_seed_override")
        dials, seed = self._compute_runtime_dials(persona, scenario)
        if isinstance(seed_override, int):
            seed = seed_override
        scenario = dict(scenario)
        scenario["interaction_contract"] = self._build_interaction_contract(persona, scenario, dials, seed)
        scenario["rng_seed"] = seed

        # Initialize conversation - start with empty messages; SUT will make first message
        messages = []
        turns = []
        api_errors = []  # Track API errors during conversation
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
            # Turn-controller state
            fields_captured: Dict[str, bool] = {k: False for k in self.analyzer.mandatory_fields.keys()}
            last_tangent_turn: int = -10
            tangent_cooldown_turns: int = 3  # allow at most one tangent every 3–4 turns
            use_controller = scenario.get('use_controller', True)
            controller_text = None  # Ensure controller_text is always defined
            for turn_idx in range(max_turns):
                # Check timeout before each turn
                elapsed_time = time.time() - simulation_start_time
                if elapsed_time >= timeout_seconds:
                    logger.warning(f"Simulation timeout reached ({elapsed_time:.1f}s >= {timeout_seconds}s) at turn {turn_idx + 1}")
                    break
                
                logger.debug(f"Starting turn {turn_idx + 1} (elapsed: {elapsed_time:.1f}s)")
                
                # SUT turn: Generate SUT response
                try:
                    sut_reply, sut_model, sut_timestamp = self._handle_sut_turn(turn_idx, messages, persona_system_prompt,
                                                    temperature=scenario.get('temperature_override'),
                                                    top_p=scenario.get('top_p_override'))
                except Exception as e:
                    api_errors.append(f"SUT API error at turn {turn_idx + 1}: {str(e)}")
                    logger.error(f"SUT turn failed at turn {turn_idx + 1}: {e}")
                    break  # End simulation on SUT failure
                turns.append({
                    "role": "system",
                    "content": sut_reply,
                    "model": sut_model,
                    "timestamp": sut_timestamp,
                    "turn_controller": None  # Never show controller for SUT turns
                })
                messages.append({"role": "assistant", "content": sut_reply})
                
                # Check if SUT provided summary
                sut_provided_summary = self.analyzer.check_sut_provided_summary(sut_reply)
                if sut_provided_summary:
                    logger.info(f"SUT provided summary at turn {turn_idx + 1}")
                
                # Update fields captured based on SUT reply (simple heuristic on field labels)
                fields_captured = self._update_fields_captured(fields_captured, sut_reply)

                # Build per-turn controller if enabled
                if use_controller:
                    controller_text, tangent_decision, clarifying_allowed = self._build_turn_controller(
                        turn_idx,
                        sut_reply,
                        fields_captured,
                        last_tangent_turn,
                        tangent_cooldown_turns,
                        scenario.get("interaction_contract", ""),
                        scenario.get("rng_seed")
                    )
                else:
                    controller_text, tangent_decision, clarifying_allowed = None, False, "no"
                scenario_turn = dict(scenario)
                scenario_turn["turn_controller"] = controller_text if use_controller else None

                # Proxy turn: Generate proxy response
                try:
                    proxy_reply, proxy_model, proxy_timestamp = self._handle_proxy_turn(
                        turn_idx, messages, sut_reply, persona, scenario_turn, persona_system_prompt, clarifying_allowed
                    )
                except Exception as e:
                    api_errors.append(f"Proxy API error at turn {turn_idx + 1}: {str(e)}")
                    logger.error(f"Proxy turn failed at turn {turn_idx + 1}: {e}")
                    break  # End simulation on proxy failure
                turns.append({
                    "role": "user",
                    "content": proxy_reply,
                    "model": proxy_model,
                    "timestamp": proxy_timestamp,
                    "turn_controller": controller_text if use_controller else None
                })
                messages.append({"role": "user", "content": proxy_reply})
                
                # After generating the proxy reply, check for clarifying questions and tangents
                if self.analyzer.check_clarifying_question(proxy_reply):
                    logger.info(f"Clarifying question detected in turn {turn_idx + 1}")

                if self.analyzer.check_tangent_inclusion(proxy_reply):
                    logger.info(f"Tangent detected in turn {turn_idx + 1}")

                # Check for conversation completion
                if sut_provided_summary and self.analyzer.check_proxy_confirmation(proxy_reply):
                    logger.info(f"Conversation completed successfully at turn {turn_idx + 1}")
                    break

                # If a tangent appears to have occurred, update last_tangent_turn
                if tangent_decision or self._detect_tangent(proxy_reply):
                    last_tangent_turn = turn_idx
            
            # Calculate final elapsed time
            final_elapsed_time = time.time() - simulation_start_time
            timeout_reached = final_elapsed_time >= timeout_seconds
            
            # Save transcript
            md_path, jsonl_path = self._save_transcript(run_id, persona, scenario, turns, output_dir, 
                                                      final_elapsed_time, timeout_reached, timeout_seconds)
            
            # Analyze conversation
            conversation_summary = self.analyzer.extract_conversation_summary(turns)
            
            # Check if proxy confirmed (look at last proxy response)
            proxy_confirmed = False
            if turns and turns[-1].get("role") == "user":
                proxy_confirmed = self.analyzer.check_proxy_confirmation(
                    turns[-1].get("content", "")
                )
            
            final_outcome = self.analyzer.determine_conversation_outcome(
                turns, sut_provided_summary, proxy_confirmed,
                timeout_reached=timeout_reached,
                api_errors=api_errors,
                elapsed_time=final_elapsed_time,
                timeout_limit=timeout_seconds
            )
            information_gathered = self.analyzer.extract_information_gathered(turns)
            
            # Update Langfuse trace
            metadata = ConversationMetadata(
                persona_name=persona["name"],
                scenario_title=scenario["title"],
                total_turns=len(turns),
                completion_status=final_outcome.status.value,  # Convert enum to string
                completion_level=final_outcome.completion_level,
                transcript_path=md_path,
                jsonl_path=jsonl_path
            )
            
            transcript_md = self._to_markdown(run_id, persona, scenario, turns, final_elapsed_time, timeout_reached, timeout_seconds, final_outcome)
            
            # Now write the markdown file with complete analysis
            with open(md_path, "w") as f:
                f.write(transcript_md)
            
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
                "jsonl_path": jsonl_path,
                "elapsed_time": final_elapsed_time,
                "timeout_reached": timeout_reached,
                "timeout_limit": timeout_seconds,
                "usage_stats": {
                    "total_tokens": self.usage_stats.total_tokens,
                    "input_tokens": self.usage_stats.total_input_tokens,
                    "output_tokens": self.usage_stats.total_output_tokens,
                    "sut_calls": self.usage_stats.sut_calls,
                    "proxy_calls": self.usage_stats.proxy_calls,
                    "estimated_cost": self.usage_stats.estimated_cost
                }
            }
            
            timeout_msg = " (TIMEOUT)" if timeout_reached else ""
            failure_msg = f" with {final_outcome.total_failures} failures" if final_outcome.total_failures > 0 else ""
            logger.info(f"Simulation completed: {final_outcome.status.value} ({final_outcome.completion_level}%) in {final_elapsed_time:.1f}s{timeout_msg}{failure_msg}")
            
            # Log detailed failure information
            if final_outcome.failures:
                logger.warning(f"Failures detected in simulation {run_id}:")
                for failure in final_outcome.failures:
                    turn_info = f" (turn {failure.turn_occurred})" if failure.turn_occurred else ""
                    logger.warning(f"  - {failure.category.value}: {failure.reason}{turn_info}")
                    if failure.error_message:
                        logger.warning(f"    Error: {failure.error_message}")
            
            if api_errors:
                logger.error(f"API errors occurred during simulation: {len(api_errors)} total")
                for error in api_errors:
                    logger.error(f"  - {error}")
            
            # Cleanup connections after simulation
            self._cleanup_connections()
            
            return results
    
    def _cleanup_connections(self):
        """Cleanup API client connections"""
        try:
            if hasattr(self.sut_client, 'close'):
                self.sut_client.close()
            if hasattr(self.proxy_client, 'close'):
                self.proxy_client.close()
            logger.debug("API client connections cleaned up")
        except Exception as e:
            logger.warning(f"Error during connection cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup connections"""
        self._cleanup_connections()
    
    def _estimate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Estimate cost based on tokens and model"""
        # Simple cost estimation - GPT-4o-mini pricing as baseline
        # Input: $0.00015 per 1K tokens, Output: $0.0006 per 1K tokens
        if "gpt-4o-mini" in model.lower():
            input_cost = (input_tokens / 1000) * 0.00015
            output_cost = (output_tokens / 1000) * 0.0006
        elif "gpt-4o" in model.lower():
            # GPT-4o pricing: Input $0.005, Output $0.015 per 1K tokens
            input_cost = (input_tokens / 1000) * 0.005
            output_cost = (output_tokens / 1000) * 0.015
        else:
            # Default to GPT-4o-mini pricing
            input_cost = (input_tokens / 1000) * 0.00015
            output_cost = (output_tokens / 1000) * 0.0006
        
        return input_cost + output_cost
    
    def _update_usage_stats(self, usage: Dict[str, Any], model: str, client_type: str):
        """Update usage statistics"""
        input_tokens = usage["input_tokens"]
        output_tokens = usage["output_tokens"]
        total_tokens = usage["total_tokens"]
        
        self.usage_stats.total_input_tokens += input_tokens
        self.usage_stats.total_output_tokens += output_tokens
        self.usage_stats.total_tokens += total_tokens
        
        if client_type == "sut":
            self.usage_stats.sut_calls += 1
        elif client_type == "proxy":
            self.usage_stats.proxy_calls += 1
        
        cost = self._estimate_cost(input_tokens, output_tokens, model)
        self.usage_stats.estimated_cost += cost
        
        logger.debug(f"{client_type.upper()} usage: {total_tokens} tokens, ${cost:.6f}, running total: ${self.usage_stats.estimated_cost:.6f}")
    
    def _handle_sut_turn(self, turn_idx: int, messages: List[Dict[str, str]], 
                        system_prompt: str, temperature: float | None = None, top_p: float | None = None) -> tuple[str, str, str]:
        """Handle a single SUT turn
        
        Returns:
            Tuple of (response_content, model_name, timestamp)
        """
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
            # Capture timestamp before API call
            timestamp = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
            
            sut_reply, sut_usage = self.sut_client.send_conversation(messages_for_sut, temperature=temperature, top_p=top_p)
            
            # Get model information from SUT client config
            model_name = self.sut_client.config.model or "unknown-model"
            
            # Enforce one-question-only where appropriate
            is_summary = self.analyzer.check_sut_provided_summary(sut_reply)
            if not is_summary:
                if turn_idx == 0:
                    sut_reply = self._enforce_single_question_first_turn(sut_reply)
                else:
                    sut_reply = self._enforce_single_question_all_turns(sut_reply)
            
            # Update usage statistics
            self._update_usage_stats(sut_usage, model_name, "sut")
            
            # Update Langfuse span with usage data
            sut_span.update(
                output={"text": sut_reply},
                usage={
                    "input": sut_usage["input_tokens"],
                    "output": sut_usage["output_tokens"],
                    "total": sut_usage["total_tokens"]
                },
                model=model_name
            )
            return sut_reply, model_name, timestamp
    
    def _handle_proxy_turn(self, turn_idx: int, messages: List[Dict[str, str]], 
                          sut_reply: str, persona: Dict[str, Any], 
                          scenario: Dict[str, Any], system_prompt: str, clarifying_allowed: str) -> tuple[str, str, str]:
        """Handle a single proxy turn
        
        Returns:
            Tuple of (response_content, model_name, timestamp)
        """
        # Use existing conversation history; last message should already be the SUT reply
        messages_for_proxy = self._sanitize_messages_for_proxy(messages)
        
        # For the first turn, inject entry_context to ground the proxy properly
        if turn_idx == 0:
            entry_context = scenario.get('entry_context', '').strip()
            if entry_context:
                # Create a synthetic first message using entry_context
                messages_for_proxy = [{"role": "user", "content": entry_context}]
        
        with self.langfuse_service.start_proxy_span(turn_idx, system_prompt, messages_for_proxy) as proxy_span:
            # Capture timestamp before API call
            timestamp = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
            
            proxy_reply, proxy_usage = self.proxy_client.send_persona_message(
                persona, scenario, messages_for_proxy
            )
            
            # Get model information from proxy client config
            model_name = self.proxy_client.config.model or "unknown-model"
            
            # Enforce clarifying/tangent only if controller is enabled
            if scenario.get('use_controller', True):
                # Prevent clarifying questions when not allowed
                if clarifying_allowed == "no":
                    # Remove common clarifying question patterns
                    import re
                    
                    # Remove multiple questions in sequence
                    proxy_reply = re.sub(r'\?[^.!]*\?', '?', proxy_reply)
                    
                    # Remove specific clarifying question patterns
                    clarifying_patterns = [
                        r'What would you do if you were in my shoes\?',
                        r'Can you clarify that\?',
                        r'What do you think\?',
                        r'What do you think would help[^?]*\?',
                        r'What would you suggest\?',
                        r'What\'s the best way to[^?]*\?',
                        r'What if we[^?]*\?',
                        r'How would you[^?]*\?',
                        r'What should I[^?]*\?',
                        r'Do you think[^?]*\?',
                        r'Would you recommend[^?]*\?',
                        r'What\'s your opinion on[^?]*\?',
                        r'How do you feel about[^?]*\?',
                        r'What\'s your take on[^?]*\?',
                        r'Any suggestions[^?]*\?',
                        r'Any advice[^?]*\?',
                        r'What would you recommend[^?]*\?',
                        r'How should I[^?]*\?',
                        r'What\'s the right approach[^?]*\?',
                        r'What do you suggest[^?]*\?',
                        r'Any thoughts on[^?]*\?',
                        r'What\'s your view on[^?]*\?',
                        r'How would you approach[^?]*\?',
                        r'What\'s your recommendation[^?]*\?',
                        r'Any ideas on[^?]*\?',
                        r'What\'s your advice[^?]*\?',
                        r'How do you see[^?]*\?',
                        r'What\'s your perspective on[^?]*\?',
                        r'Any recommendations[^?]*\?',
                        r'What would you advise[^?]*\?',
                        r'How would you handle[^?]*\?',
                        r'What\'s the best approach[^?]*\?',
                        r'Any guidance[^?]*\?',
                        r'What\'s your suggestion[^?]*\?',
                        r'How should we[^?]*\?',
                        r'What do you recommend[^?]*\?',
                        r'Any tips on[^?]*\?',
                        r'What\'s your input on[^?]*\?',
                        r'How would you suggest[^?]*\?',
                        r'What\'s your guidance[^?]*\?',
                        r'Any suggestions for[^?]*\?',
                        r'What would you propose[^?]*\?',
                        r'How do you recommend[^?]*\?',
                        r'What\'s your recommendation for[^?]*\?',
                        r'Any advice on[^?]*\?',
                        r'What\'s your take on[^?]*\?',
                        r'How would you recommend[^?]*\?',
                        r'What do you think about[^?]*\?',
                        r'Any thoughts about[^?]*\?',
                        r'What\'s your opinion about[^?]*\?',
                        r'How do you feel about[^?]*\?',
                        r'What\'s your view about[^?]*\?',
                        r'How would you approach[^?]*\?',
                        r'What\'s your perspective about[^?]*\?',
                        r'Any ideas about[^?]*\?',
                        r'What\'s your advice about[^?]*\?',
                        r'How do you see[^?]*\?',
                        r'What\'s your suggestion about[^?]*\?',
                        r'How should we approach[^?]*\?',
                        r'What do you recommend about[^?]*\?',
                        r'Any tips about[^?]*\?',
                        r'What\'s your input about[^?]*\?',
                        r'How would you suggest about[^?]*\?',
                        r'What\'s your guidance about[^?]*\?',
                        r'Any suggestions about[^?]*\?',
                        r'What would you propose about[^?]*\?',
                        r'How do you recommend about[^?]*\?',
                        r'What\'s your recommendation about[^?]*\?',
                        r'Any advice about[^?]*\?',
                        r'What\'s your take about[^?]*\?',
                        r'How would you recommend about[^?]*\?'
                    ]
                    
                    # Apply all clarifying question patterns
                    for pattern in clarifying_patterns:
                        proxy_reply = re.sub(pattern, '', proxy_reply, flags=re.IGNORECASE)
                    
                    # Clean up any remaining question marks at the end
                    proxy_reply = re.sub(r'\s*\?\s*$', '', proxy_reply)
                    
                    # Clean up extra whitespace and punctuation
                    proxy_reply = re.sub(r'\s+', ' ', proxy_reply)
                    proxy_reply = re.sub(r'\s*,\s*$', '', proxy_reply)
                    proxy_reply = re.sub(r'\s*\.\s*$', '', proxy_reply)
                    proxy_reply = proxy_reply.strip()
                
                # Enforce clarifying question if allowed and uncertainty is detected
                if clarifying_allowed == "yes" and self._detect_uncertainty(sut_reply):
                    proxy_reply += " Can you clarify that?"
                # Enforce tangent if allowed
                tangent_allowed = scenario.get("turn_controller", "").find("tangent_allowed: yes") != -1
                if tangent_allowed:
                    proxy_reply += " By the way, did you know... Anyway, "
                    proxy_reply += "What were we discussing?"
            # Update usage statistics
            self._update_usage_stats(proxy_usage, model_name, "proxy")
            
            # Update Langfuse span with usage data
            proxy_span.update(
                output={"text": proxy_reply},
                usage={
                    "input": proxy_usage["input_tokens"],
                    "output": proxy_usage["output_tokens"],
                    "total": proxy_usage["total_tokens"]
                },
                model=model_name
            )
            return proxy_reply, model_name, timestamp

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

Example (acceptable): "Hi 👋 Welcome to Staffer. I'm your AI-powered recruiter, and I'm here to help you find your next great hire, faster.

To get started and ensure I provide you with the best possible help, I'd love to learn a bit about your hiring needs."

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
            prompt_path = Path(self.sut_prompt_path)
            if prompt_path.exists():
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logger.warning(f"Recruiter prompt file not found at {self.sut_prompt_path}, using fallback")
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

    # ------------------------------
    # Turn controller helpers
    # ------------------------------
    def _update_fields_captured(self, fields_captured: Dict[str, bool], sut_reply: str) -> Dict[str, bool]:
        """Heuristic: mark a field captured if SUT asked and received confirmation-like phrasing in prior messages.

        Here we simply detect if SUT mentions a mandatory field label followed by a colon.
        This is a minimal placeholder and can be upgraded to parse conversation state.
        """
        try:
            text = (sut_reply or "").lower()
            updated = dict(fields_captured)
            for analysis_key, label in self.analyzer.mandatory_fields.items():
                label_lower = label.lower().rstrip(":")
                if f"{label_lower}:" in text:
                    updated[analysis_key] = True
            return updated
        except Exception:
            return fields_captured

    def _detect_uncertainty(self, text: str) -> bool:
        """Detect uncertainty phrases in proxy intent triggers."""
        if not text:
            return False
        t = text.lower()
        phrases = [
            "i'm not sure", "i dont know", "i don't know", "not certain",
            "unsure", "maybe", "i think", "market's crazy", "am i being too picky"
        ]
        return any(p in t for p in phrases)

    def _detect_tangent(self, proxy_reply: str) -> bool:
        """Minimal tangent heuristic: presence of 'anyway' or 'side note' often marks a micro-detour."""
        if not proxy_reply:
            return False
        t = proxy_reply.lower()
        return ("anyway" in t) or ("side note" in t) or ("btw" in t)

    def _build_turn_controller(
        self,
        turn_idx: int,
        sut_reply: str,
        fields_captured: Dict[str, bool],
        last_tangent_turn: int,
        tangent_cooldown_turns: int,
        contract: str,
        seed: int,
    ) -> tuple[str, bool, str]:
        """Create a compact controller block for this turn using scenario dials embedded in contract text.

        Returns (controller_text, tangent_decision_bool)
        """
        # Extract dials from the contract text (simple regex fallback)
        import re

        def _extract_float(name: str, default: float) -> float:
            try:
                m = re.search(rf"{name}\s*:\s*([0-9]*\.?[0-9]+)", contract)
                if m:
                    return float(m.group(1))
            except Exception:
                pass
            return default

        clar_prob = _extract_float("clarifying_question_prob", 0.4)
        tangent_prob = _extract_float("tangent_prob_after_field", 0.2)

        # Determine if a field was just captured this turn by diffing keys mentioned in this SUT reply
        field_just_captured = False
        try:
            text = (sut_reply or "").lower()
            for _, label in self.analyzer.mandatory_fields.items():
                label_lower = label.lower().rstrip(":")
                if f"{label_lower}:" in text:
                    field_just_captured = True
                    break
        except Exception:
            field_just_captured = False

        # Seeded RNG for decisions
        def _rand_01(seed_val: int, turn: int, kind: str) -> float:
            import hashlib
            payload = f"{seed_val}:{turn}:{kind}".encode("utf-8")
            h = hashlib.sha256(payload).hexdigest()
            # Take first 8 hex chars => 32 bits => int, map to [0,1)
            n = int(h[:8], 16)
            return (n % 10_000_000) / 10_000_000.0

        # Clarifying allowed only when uncertainty detected in prior proxy content; since we cannot
        # inspect future proxy text, we gate via roll here and communicate YES/NO with threshold.
        clar_roll = _rand_01(seed or 0, turn_idx, "clarify")
        clarifying_allowed = "yes" if clar_roll < clar_prob else "no"

        # Tangent allowed only if cooldown elapsed and a field was just captured
        cooldown_remaining = max(0, (last_tangent_turn + tangent_cooldown_turns) - turn_idx)
        tangent_gate = (cooldown_remaining <= 0 and field_just_captured)
        tangent_roll = _rand_01(seed or 0, turn_idx, "tangent") if tangent_gate else 1.0
        tangent_decision = tangent_gate and (tangent_roll < tangent_prob)
        tangent_allowed = "yes" if tangent_decision else "no"

        # Update controller wording to reflect binding decisions in deterministic mode
        lines = [
            "TURN CONTROLLER:",
            f"- clarifying_allowed: {clarifying_allowed} (roll: {clar_roll:.2f} < {clar_prob:.2f} if uncertainty phrase)",
            f"- tangent_allowed: {tangent_allowed} (roll: {tangent_roll:.2f} < {tangent_prob:.2f}; cooldown: {cooldown_remaining}; field_just_captured: {str(field_just_captured).lower()})",
            "- on_summary: confirm succinctly with approved closure phrasing",
            "- resume_policy: after any tangent, answer the recruiter's last question directly",
            "- deterministic_mode: binding decisions enforced"
        ]
        return "\n".join(lines), tangent_decision, clarifying_allowed
