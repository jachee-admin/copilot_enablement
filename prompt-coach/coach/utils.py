from __future__ import annotations
import os, difflib, json
from dataclasses import dataclass

def get_model() -> str:
    return os.getenv("PROMPT_COACH_MODEL", "gpt-4o-mini")

def get_timeout() -> float:
    return float(os.getenv("PROMPT_COACH_TIMEOUT", "30"))

@dataclass
class ModelUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""

def unified_diff(a: str, b: str) -> str:
    a_lines = a.splitlines(keepends=True)
    b_lines = b.splitlines(keepends=True)
    return "".join(difflib.unified_diff(a_lines, b_lines, fromfile="original", tofile="improved"))

def safe_json_loads(s: str) -> dict:
    try:
        return json.loads(s)
    except Exception:
        return {"scorecard": {}, "improved": s, "verification": [], "notes": ["non-json model output"]}
