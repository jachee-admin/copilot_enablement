import os, json
from typing import Dict, Any, Tuple
from openai import OpenAI
from .utils import get_model, get_timeout, ModelUsage, safe_json_loads
from dotenv import load_dotenv
load_dotenv()

def get_client() -> OpenAI:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAI(api_key=key)

def judge_and_rewrite(system_prompt: str, user_prompt: str) -> Tuple[Dict[str, Any], ModelUsage]:
    client = get_client()
    model = get_model()
    timeout = get_timeout()

    # Prepare base request parameters
    request_params = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "timeout": timeout,
        "temperature": 0.2,  # Try with custom temperature first
    }

    try:
        r = client.chat.completions.create(**request_params)
    except Exception as e:
        # If we get an error about unsupported temperature, retry without it
        if "temperature" in str(e) and "unsupported" in str(e).lower():
            request_params.pop("temperature")  # Remove temperature parameter
            r = client.chat.completions.create(**request_params)
        else:
            raise  # Re-raise if it's a different error

    content = r.choices[0].message.content or "{}"
    data = safe_json_loads(content)
    u = r.usage
    usage = ModelUsage(
        prompt_tokens=getattr(u, "prompt_tokens", 0),
        completion_tokens=getattr(u, "completion_tokens", 0),
        total_tokens=getattr(u, "total_tokens", 0),
        model=model,
    )
    return data, usage
