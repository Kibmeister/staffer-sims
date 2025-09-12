# simulate.py
import os, json, time, uuid, yaml, argparse
from datetime import datetime
from typing import List, Dict
import requests
import logging

# pip install langfuse pyyaml python-dotenv
from langfuse import Langfuse
from dotenv import load_dotenv

# Load .env file first
load_dotenv()

# Import our new configuration system
from config.env_loader import load_environment_config
from config.settings import get_settings

### ---------- helpers ----------
def load_yaml(p): 
    with open(p, "r") as f: return yaml.safe_load(f)

def now_id(): return datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S") + f"_run-{uuid.uuid4().hex[:6]}"

### ---------- SUT + Proxy wiring ----------
def send_sut(sut_cfg: dict, messages: List[Dict]) -> str:
    """Call your Staffer chat endpoint with full convo history."""
    url = sut_cfg["url"]
    headers = sut_cfg.get("headers", {})
    payload = {"messages": messages}  # adapt to your API contract
    print("[send_sut] Payload:", payload)
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    try:
        r.raise_for_status()
        data = r.json()
        # Try OpenAI format first
        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"]
        # Otherwise, expect Staffer SUT format
        if "message" in data:
            return data["message"]
        print("[send_sut] Unexpected response format:", data)
        raise KeyError("Response missing 'message' or 'choices[0][\"message\"][\"content\"]' key")
    except Exception as e:
        print("[send_sut] Exception:", e)
        print("[send_sut] Response text:", r.text)
        raise

def send_proxy_user(proxy_cfg: dict, persona: dict, scenario: dict, messages: List[Dict]) -> str:
    """Role-play the persona with your LLM provider (replace with your SDK)."""
    # Build a strict, explicit system prompt for the proxy user from persona and scenario fields
    system = (
        f"{persona.get('role_adherence', '')}\n"
        f"FORBIDDEN BEHAVIORS:\n" + '\n'.join(persona.get('forbidden_behaviors', [])) + "\n"
        f"REQUIRED BEHAVIORS:\n" + '\n'.join(persona.get('required_behaviors', [])) + "\n"
        f"RESPONSE FORMULA: {persona.get('response_formula', '')}\n"
        f"RECOVERY PHRASE: {persona.get('recovery_phrase', '')}\n"
        f"CHARACTER MOTIVATION: {persona.get('character_motivation', '')}\n"
        f"{scenario.get('role_adherence', '')}\n"
        f"FORBIDDEN BEHAVIORS (scenario):\n" + '\n'.join(scenario.get('forbidden_behaviors', [])) + "\n"
        f"REQUIRED BEHAVIORS (scenario):\n" + '\n'.join(scenario.get('required_behaviors', [])) + "\n"
        f"RESPONSE FORMULA (scenario): {scenario.get('response_formula', '')}\n"
        f"RECOVERY PHRASE (scenario): {scenario.get('recovery_phrase', '')}\n"
        f"CHARACTER MOTIVATION (scenario): {scenario.get('character_motivation', '')}\n"
    )
    url = proxy_cfg["url"]
    headers = proxy_cfg.get("headers", {})
    payload = {
        "model": proxy_cfg.get("model", "gpt-4o-mini"),
        "messages": [{"role": "system", "content": system}] + messages
    }
    print("[send_proxy_user] Payload:", payload)
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    try:
        r.raise_for_status()
        data = r.json()
        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"]
        print("[send_proxy_user] Unexpected response format:", data)
        raise KeyError("Response missing 'choices[0][\"message\"][\"content\"]' key")
    except Exception as e:
        print("[send_proxy_user] Exception:", e)
        print("[send_proxy_user] Response text:", r.text)
        raise

### ---------- Judge (Critique) ----------
# judge_transcript function removed - now using Langfuse evaluations

### ---------- Langfuse ----------
def init_langfuse(cfg):
    return Langfuse(
        public_key=cfg["public_key"],
        secret_key=cfg["secret_key"],
        host=cfg.get("host")  # optional for self-hosted
    )

def extract_conversation_summary(turns):
    """Extract a comprehensive summary of the conversation."""
    summary = {
        "total_turns": len(turns),
        "conversation_flow": [],
        "key_information_gathered": [],
        "conversation_quality": "unknown"
    }
    
    # Extract conversation flow
    for i, turn in enumerate(turns):
        role = turn.get("role", "unknown")
        content = turn.get("content", "")
        summary["conversation_flow"].append({
            "turn": i + 1,
            "role": role,
            "content_preview": content[:100] + "..." if len(content) > 100 else content
        })
    
    # Extract key information (look for structured data in SUT responses)
    for turn in turns:
        if turn.get("role") == "system":  # SUT responses
            content = turn.get("content", "").lower()
            if "job title:" in content or "salary range:" in content or "experience level:" in content:
                summary["key_information_gathered"].append("role_requirements")
            if "location:" in content or "remote" in content:
                summary["key_information_gathered"].append("work_location")
            if "skills:" in content or "technologies:" in content:
                summary["key_information_gathered"].append("technical_skills")
    
    return summary

def determine_conversation_outcome(turns, sut_provided_summary, proxy_confirmed):
    """Determine the final outcome of the conversation."""
    outcome = {
        "status": "incomplete",
        "completion_level": 0,
        "success_indicators": [],
        "issues": []
    }
    
    # Check for successful completion
    if sut_provided_summary and proxy_confirmed:
        outcome["status"] = "completed_successfully"
        outcome["completion_level"] = 100
        outcome["success_indicators"].append("role_summary_provided")
        outcome["success_indicators"].append("user_confirmed_summary")
    elif sut_provided_summary:
        outcome["status"] = "summary_provided_awaiting_confirmation"
        outcome["completion_level"] = 80
        outcome["success_indicators"].append("role_summary_provided")
        outcome["issues"].append("user_did_not_confirm")
    else:
        outcome["status"] = "incomplete"
        outcome["completion_level"] = 50
        outcome["issues"].append("no_role_summary_provided")
    
    # Check for role-playing quality
    for turn in turns:
        if turn.get("role") == "user":  # Proxy responses
            content = turn.get("content", "").lower()
            if "sorry, i'm the one who needs help" in content:
                outcome["success_indicators"].append("role_adherence_maintained")
            if "drowning in work" in content or "systems are getting hammered" in content:
                outcome["success_indicators"].append("persona_characteristics_expressed")
    
    return outcome

def extract_information_gathered(turns):
    """Extract structured information that was gathered during the conversation."""
    info = {
        "role_type": None,
        "location": None,
        "employment_type": None,
        "experience_level": None,
        "salary_range": None,
        "skills_mentioned": [],
        "responsibilities": [],
        "deadline": None
    }
    
    # Look for structured information in SUT responses
    for turn in turns:
        if turn.get("role") == "system":  # SUT responses
            content = turn.get("content", "")
            
            # Extract role type
            if "senior backend engineer" in content.lower():
                info["role_type"] = "Senior Backend Engineer"
            
            # Extract location
            if "san francisco" in content.lower():
                info["location"] = "San Francisco"
            elif "remote" in content.lower():
                info["location"] = "Remote"
            
            # Extract employment type
            if "full-time" in content.lower():
                info["employment_type"] = "Full-time"
            elif "part-time" in content.lower():
                info["employment_type"] = "Part-time"
            elif "contract" in content.lower():
                info["employment_type"] = "Contract"
            
            # Extract experience level
            if "5-7 years" in content or "5 to 7 years" in content:
                info["experience_level"] = "5-7 years"
            elif "senior" in content.lower():
                info["experience_level"] = "Senior level"
            
            # Extract salary range
            if "$" in content:
                import re
                salary_match = re.search(r'\$[\d,]+(?:-\$[\d,]+)?', content)
                if salary_match:
                    info["salary_range"] = salary_match.group()
            
            # Extract skills
            if "node.js" in content.lower():
                info["skills_mentioned"].append("Node.js")
            if "java" in content.lower():
                info["skills_mentioned"].append("Java")
            if "python" in content.lower():
                info["skills_mentioned"].append("Python")
            if "aws" in content.lower():
                info["skills_mentioned"].append("AWS")
            if "microservices" in content.lower():
                info["skills_mentioned"].append("Microservices")
            if "postgresql" in content.lower():
                info["skills_mentioned"].append("PostgreSQL")
    
    return info

### ---------- Transcript export ----------
def to_markdown(run_id, persona, scenario, turns):
    lines = [f"# Transcript {run_id}", f"**Persona:** {persona['name']}  \n**Scenario:** {scenario['title']}", ""]
    for t in turns:
        lines.append(f"**{t['role'].title()}**: {t['content']}")
    return "\n\n".join(lines)

### ---------- Main loop ----------
def simulate(args):
    # Load environment configuration
    load_environment_config()
    
    # Get settings instance
    settings = get_settings()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=settings.log_format
    )
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting simulation in {settings.environment} environment")
    logger.debug(f"Configuration: {settings.to_dict()}")
    
    persona = load_yaml(args.persona)
    scenario = load_yaml(args.scenario)
    
    # Use new configuration system instead of YAML files
    sut_cfg = settings.get_sut_config()
    lf_cfg = settings.get_langfuse_config()
    proxy_cfg = settings.get_proxy_api_config()

    lf = init_langfuse(lf_cfg)
    run_id = now_id()
    turns = []
    max_turns = scenario.get("max_turns", settings.max_turns)

    # Kickoff: either SUT greets or proxy states the need
    messages = [{"role":"user","content": scenario.get("entry_context","I want to hire.")}]

    system = (
        f"You role-play {persona['name']}, a {persona['role']}. "
        f"Style: {persona.get('voice','concise')}. "
        f"Goals: {', '.join(persona.get('goals', [])).strip()}. "
        "Provide multiple details in one message when asked for basics. "
        "If unsure, ask 1 clarifying question; otherwise answer naturally."
    )
    # Create the main trace using the correct Langfuse API
    with lf.start_as_current_observation(
        as_type='span',
        name="persona_simulation",
        input={
            "persona": persona["name"],
            "scenario": scenario["title"]
        },
        metadata={
            "role": persona["role"],
            "entry": scenario["entry_context"]
        }
    ) as trace:
        # Set comprehensive tags for filtering and grouping
        lf.update_current_trace(tags=[
            persona["name"], 
            scenario["title"]
        ])
        for turn_idx in range(max_turns):
            # SUT reply
            messages_for_sut = (
                [{"role": "system", "content": "You are the recruiter assistant. The user is the hiring manager."}] + messages
            )
            with lf.start_as_current_observation(
                as_type='span',
                name="sut_message",
                input={"messages": messages_for_sut},
                metadata={"turn": turn_idx, "activity": "sut_message", "model": "staffer-sut"}
            ) as sut_span:
                sut_reply = send_sut(sut_cfg, messages_for_sut)
                turns.append({"role":"system", "content": sut_reply})
                sut_span.update(output={"text":sut_reply})

            # Check if SUT provided a summary (but don't stop yet)
            summary_phrases = [
                "here's the role", "here is the role", "to summarize", "summary of the role",
                "candidate preview", "publish", "job description", "role summary",
                "should i lock these in", "great, i've got everything"
            ]
            sut_provided_summary = any(phrase in sut_reply.lower() for phrase in summary_phrases)

            # Proxy reply
            messages_for_proxy = (
                [{"role": "system", "content": "You are the hiring manager. The assistant is the recruiter."}] + messages + [{"role":"assistant","content": sut_reply}]
            )
            proxy_input = {
                "system": system,
                "messages": messages_for_proxy
            }
            with lf.start_as_current_observation(
                as_type='span',
                name="proxy_message",
                input=proxy_input,
                metadata={"turn": turn_idx, "activity": "proxy_message", "system_prompt": system, "model": "gpt-4"}
            ) as proxy_span:
                proxy_reply = send_proxy_user(proxy_cfg, persona, scenario, messages_for_proxy)
                turns.append({"role":"user", "content": proxy_reply})
                proxy_span.update(output={"text":proxy_reply})

            # Check if user confirmed the summary (stop after confirmation)
            if sut_provided_summary:
                confirmation_phrases = [
                    "yes", "looks good", "that's correct", "perfect", "sounds good",
                    "that works", "confirmed", "accurate", "exactly what i need"
                ]
                if any(phrase in proxy_reply.lower() for phrase in confirmation_phrases):
                    break

            messages.extend([
                {"role":"assistant","content": sut_reply},
                {"role":"user","content": proxy_reply}
            ])

        # Export transcript
        output_dir = args.output if hasattr(args, 'output') and args.output else settings.output_dir
        os.makedirs(output_dir, exist_ok=True)
        md = to_markdown(run_id, persona, scenario, turns)
        md_path = os.path.join(output_dir, f"{run_id}.md")
        with open(md_path, "w") as f: f.write(md)

        jsonl_path = os.path.join(output_dir, f"{run_id}.jsonl")
        with open(jsonl_path, "w") as f:
            for t in turns: f.write(json.dumps(t, ensure_ascii=False) + "\n")

        # Extract conversation analysis
        conversation_summary = extract_conversation_summary(turns)
        
        # Check if proxy confirmed (look at last proxy response)
        proxy_confirmed = False
        if turns and turns[-1].get("role") == "user":
            last_proxy_response = turns[-1].get("content", "").lower()
            confirmation_phrases = ["yes", "looks good", "that's correct", "perfect", "sounds good", "that works", "confirmed", "accurate", "exactly what i need"]
            proxy_confirmed = any(phrase in last_proxy_response for phrase in confirmation_phrases)
        
        final_outcome = determine_conversation_outcome(turns, sut_provided_summary, proxy_confirmed)
        information_gathered = extract_information_gathered(turns)
        
        # Update trace with comprehensive output
        lf.update_current_trace(
            output={
                "conversation_summary": conversation_summary,
                "final_outcome": final_outcome,
                "total_turns": len(turns),
                "information_gathered": information_gathered,
                "transcript": md,
                "persona": persona["name"],
                "scenario": scenario["title"]
            },
            metadata={
                "transcript_path": md_path, 
                "jsonl_path": jsonl_path,
                "completion_status": final_outcome["status"],
                "completion_level": final_outcome["completion_level"]
            }
        )
        
        # Langfuse Evaluations (replaces custom judge logic)
        # Create a comprehensive evaluation event
        lf.create_event(
            name="conversation_evaluation",
            input=md,
            output={
                "transcript": md, 
                "turns": len(turns), 
                "persona": persona["name"], 
                "scenario": scenario["title"],
                "conversation_summary": conversation_summary,
                "final_outcome": final_outcome,
                "information_gathered": information_gathered
            }
        )
        
        # Note: Individual scores will be created by Langfuse's configured evaluations
        # This event triggers the evaluation pipeline in Langfuse
        # Flush to ensure data is sent to Langfuse
        lf.flush()
        
        print(f"Saved: {md_path}\nSaved: {jsonl_path}")
        print(f"Conversation Outcome: {final_outcome['status']} (Level: {final_outcome['completion_level']}%)")
        print(f"Information Gathered: {len(information_gathered['skills_mentioned'])} skills, Role: {information_gathered['role_type']}, Location: {information_gathered['location']}")
        print("Evaluations: Sent to Langfuse for processing")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", required=True)
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--sut", default="config/sut.yml")
    ap.add_argument("--proxy", default="config/proxy.yml")
    ap.add_argument("--langfuse", default="config/langfuse.yml")
    # --judge argument removed - now using Langfuse evaluations
    ap.add_argument("--output", default="output")
    args = ap.parse_args()
    simulate(args)
