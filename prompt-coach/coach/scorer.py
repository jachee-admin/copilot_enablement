from typing import Dict, Any
from .heuristics import score_prompt, total
from .templates import SYSTEM_PROMPT
from .openai_client import judge_and_rewrite

def score_and_improve(raw_prompt: str) -> Dict[str, Any]:
    h = score_prompt(raw_prompt)
    local_score = total(h)

    model = judge_and_rewrite(SYSTEM_PROMPT, raw_prompt)
    # model["scorecard"] expected: dict with the same sub-keys and total
    model_score = model["scorecard"].get("total", 0)

    final = round((local_score + model_score) / 2)
    improved = model.get("improved", raw_prompt)

    return {
        "local_score": local_score,
        "model_score": model_score,
        "final_score": final,
        "scorecard": model.get("scorecard", {}),
        "improved": improved,
        "verification": model.get("verification", []),
        "notes": model.get("notes", []),
    }
