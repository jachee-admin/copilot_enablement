import re
from dataclasses import dataclass

@dataclass
class HeuristicScores:
    clarity: int
    context: int
    constraints: int
    format_contract: int
    guardrails: int
    acceptance: int

KEY_SIGNS = {
    "role": r"\bAct as\b|\bRole\b",
    "format": r"\bRespond only with\b|\bOutput\b.*(JSON|YAML|table|code only)",
    "guardrails": r"\bDo not fabricate\b|\bverification\b|\bcommands to verify\b",
    "accept": r"\bAcceptance\b|\bAcceptance Criteria\b|\btests\b|\bvalidation\b",
}

def score_prompt(text: str) -> HeuristicScores:
    t = text.strip()
    clarity = 20 if len(t.split()) >= 6 and ("Task:" in t or "Write" in t or "Create" in t) else 12
    context = 20 if any(k in t for k in ["RHEL","PostgreSQL","Python","Ansible","versions","constraints"]) else 8
    constraints = 15 if any(k in t for k in ["idempotent","no shell","lint","type hints","RLS","security"]) else 7
    format_contract = 20 if re.search(KEY_SIGNS["format"], t, re.I) else 8
    guardrails = 15 if re.search(KEY_SIGNS["guardrails"], t, re.I) else 6
    acceptance = 10 if re.search(KEY_SIGNS["accept"], t, re.I) else 4
    return HeuristicScores(clarity, context, constraints, format_contract, guardrails, acceptance)

def total(h: HeuristicScores) -> int:
    return h.clarity + h.context + h.constraints + h.format_contract + h.guardrails + h.acceptance
