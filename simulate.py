# simulate.py
import os, json, time, uuid, yaml, argparse
from datetime import datetime
from typing import List, Dict
import requests

# pip install langfuse pyyaml python-dotenv
from langfuse import Langfuse

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
        "model": "gpt-4",  # or your preferred model
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
def judge_transcript(judge_cfg: dict, transcript_md: str) -> Dict:
    """Ask an LLM to score the run and suggest improvements."""
    rubric = load_yaml(judge_cfg["rubric_path"])
    prompt = f"""
You are a senior Conversation Designer and Copywriter.
Score the transcript below using these metrics (0–5): {rubric['metrics']}.
Return JSON with: scores, top_issues (5 bullets), prompt_deltas (edits to system prompt),
copy_fixes (3 rewrites), next_experiment (one idea).

Transcript (Markdown):
{transcript_md}
"""
    url = judge_cfg["url"]
    headers = judge_cfg.get("headers", {})
    payload = {"prompt": prompt}
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()  # expects a dict with keys described above

### ---------- Langfuse ----------
def init_langfuse(cfg):
    return Langfuse(
        public_key=cfg["public_key"],
        secret_key=cfg["secret_key"],
        host=cfg.get("host")  # optional for self-hosted
    )

### ---------- Transcript export ----------
def to_markdown(run_id, persona, scenario, turns):
    lines = [f"# Transcript {run_id}", f"**Persona:** {persona['name']}  \n**Scenario:** {scenario['title']}", ""]
    for t in turns:
        lines.append(f"**{t['role'].title()}**: {t['content']}")
    return "\n\n".join(lines)

### ---------- Main loop ----------
def simulate(args):
    persona = load_yaml(args.persona)
    scenario = load_yaml(args.scenario)
    sut_cfg = load_yaml(args.sut)
    lf_cfg = load_yaml(args.langfuse)
    proxy_cfg = load_yaml(args.proxy)
    judge_cfg = load_yaml(args.judge)

    lf = init_langfuse(lf_cfg)
    run_id = now_id()
    turns = []
    max_turns = scenario.get("max_turns", 18)

    # Kickoff: either SUT greets or proxy states the need
    messages = [{"role":"user","content": scenario.get("entry_context","I want to hire.")}]

    system = (
        f"You role-play {persona['name']}, a {persona['role']}. "
        f"Style: {persona.get('voice','concise')}. "
        f"Goals: {', '.join(persona.get('goals', [])).strip()}. "
        "Provide multiple details in one message when asked for basics. "
        "If unsure, ask 1 clarifying question; otherwise answer naturally."
    )
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
    ) as trace_span:
        lf.update_current_trace(tags=[persona["name"], scenario["title"]])
        for turn_idx in range(max_turns):
            # SUT reply
            messages_for_sut = (
                [{"role": "system", "content": "You are the recruiter assistant. The user is the hiring manager."}] + messages
            )
            with trace_span.start_as_current_observation(
                as_type='span',
                name="sut_message",
                input={"messages": messages_for_sut},
                metadata={"turn": turn_idx, "activity": "sut_message"}
            ) as sut_span:
                sut_reply = send_sut(sut_cfg, messages_for_sut)
                turns.append({"role":"system", "content": sut_reply})
                sut_span.update(output={"text":sut_reply})

            # Stop conditions (simple keywords; refine as needed)
            if any(k in sut_reply.lower() for k in ["here's the role", "candidate preview", "publish"]):
                break

            # Proxy reply
            messages_for_proxy = (
                [{"role": "system", "content": "You are the hiring manager. The assistant is the recruiter."}] + messages + [{"role":"assistant","content": sut_reply}]
            )
            proxy_input = {
                "system": system,
                "messages": messages_for_proxy
            }
            with trace_span.start_as_current_observation(
                as_type='span',
                name="proxy_message",
                input=proxy_input,
                metadata={"turn": turn_idx, "activity": "proxy_message", "system_prompt": system}
            ) as proxy_span:
                proxy_reply = send_proxy_user(proxy_cfg, persona, scenario, messages_for_proxy)
                turns.append({"role":"user", "content": proxy_reply})
                proxy_span.update(output={"text":proxy_reply})

            messages.extend([
                {"role":"assistant","content": sut_reply},
                {"role":"user","content": proxy_reply}
            ])

        # Export transcript
        os.makedirs(args.output, exist_ok=True)
        md = to_markdown(run_id, persona, scenario, turns)
        md_path = os.path.join(args.output, f"{run_id}.md")
        with open(md_path, "w") as f: f.write(md)

        jsonl_path = os.path.join(args.output, f"{run_id}.jsonl")
        with open(jsonl_path, "w") as f:
            for t in turns: f.write(json.dumps(t, ensure_ascii=False) + "\n")

        # Judge
        critique = judge_transcript(judge_cfg, md)
        lf.create_event(name="critique", output=critique)
        lf.update_current_trace(metadata={"transcript_path": md_path, "jsonl_path": jsonl_path})
        print(f"Saved: {md_path}\nSaved: {jsonl_path}\nScores: {critique.get('scores')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", required=True)
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--sut", default="config/sut.yml")
    ap.add_argument("--proxy", default="config/proxy.yml")
    ap.add_argument("--langfuse", default="config/langfuse.yml")
    ap.add_argument("--judge", default="config/judge.yml")
    ap.add_argument("--output", default="output")
    args = ap.parse_args()
    simulate(args)
