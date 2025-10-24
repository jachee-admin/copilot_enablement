import os
from typing import Dict, Any
from openai import OpenAI

def get_client() -> OpenAI:
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def judge_and_rewrite(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    client = get_client()
    r = client.chat.completions.create(
        model="gpt-4o-mini",  # cost-effective; adjust as you like
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    content = r.choices[0].message.content
    import json
    return json.loads(content)
