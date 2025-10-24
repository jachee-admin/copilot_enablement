from typing import Dict, Any
from .heuristics import score_prompt, total
from .templates import SYSTEM_PROMPT
from .openai_client import judge_and_rewrite
from .utils import unified_diff

def score_and_improve(raw_prompt: str) -> Dict[str, Any]:
    h = score_prompt(raw_prompt)
    local_score = total(h)

    model_data, usage = judge_and_rewrite(SYSTEM_PROMPT, raw_prompt)
    model_score = model_data.get("scorecard", {}).get("total", 0)
    improved = model_data.get("improved", raw_prompt)
    verification = model_data.get("verification", [])
    notes = model_data.get("notes", [])
    scorecard = model_data.get("scorecard", {})

    final = round((local_score + (model_score or 0)) / 2)
    return {
        "local_score": local_score,
        "model_score": model_score,
        "final_score": final,
        "scorecard": scorecard,
        "improved": improved,
        "diff": unified_diff(raw_prompt, improved),
        "verification": verification,
        "notes": notes,
        "usage": {
            "model": usage.model,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        },
    }
