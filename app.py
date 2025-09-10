# app.py
import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import requests
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

def load_system_prompt(prompt_name="recruiter_v1.txt"):
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", prompt_name)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

SYSTEM_PROMPT = load_system_prompt(os.getenv("SUT_PROMPT", "recruiter_v1.txt"))

class Message(BaseModel):
    role: str
    content: str

class Config(BaseModel):
    model: str = "gpt-4"
    temperature: float = 0.2

class Trace(BaseModel):
    trace_id: Optional[str] = None
    tags: Optional[List[str]] = None

class ChatRequest(BaseModel):
    messages: List[Message]
    config: Optional[Config] = Config()
    trace: Optional[Trace] = None

class ChatResponse(BaseModel):
    message: str
    meta: Dict[str, Any] = Field(default_factory=dict)

app = FastAPI(title="Staffer SUT Chat API")

@app.get("/")
def root():
    return {"message": "Staffer SUT API is running!"}

def call_openai(messages: List[Dict[str, str]], cfg: Config) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": cfg.model,
        "temperature": cfg.temperature,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    }
    r = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=60)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=r.text)
    return r.json()

def naive_slot_extract(history_text: str) -> Dict[str, Any]:
    # keep simple; you can replace with a proper extractor later
    return {
        "title": "Senior Backend Engineer" if "Senior Backend Engineer" in history_text else None,
        "employment_type": None,
        "work_mode": None,
        "location": None
    }

@app.post("/sut/chat", response_model=ChatResponse)
def sut_chat(req: ChatRequest):
    # Build LLM messages
    llm_msgs = [{"role": m.role, "content": m.content} for m in req.messages]

    data = call_openai(llm_msgs, req.config)
    choice = data["choices"][0]
    text = choice["message"]["content"]
    usage = data.get("usage", {})

    full_history = " ".join([m["content"] for m in llm_msgs])
    slots = naive_slot_extract(full_history)

    resp = ChatResponse(
        message=text,
        meta={
            "tokens_prompt": usage.get("prompt_tokens"),
            "tokens_completion": usage.get("completion_tokens"),
            "finish_reason": choice.get("finish_reason", "stop"),
            "module_hint": "role_basics",  # optional: set heuristically or via small classifier
            "slots_extracted": slots
        }
    )
    return resp
