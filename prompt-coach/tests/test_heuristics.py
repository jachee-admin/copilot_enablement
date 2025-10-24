from coach.heuristics import score_prompt, total

def test_heuristics_detects_format_and_guardrails():
    txt = """Act as a senior Ansible reviewer.
    Context: RHEL9, Postgres 16.
    Task: Write idempotent playbook.
    Respond only with YAML.
    Do not fabricate; if unsure, suggest commands to verify.
    Acceptance: passes ansible-lint."""
    s = score_prompt(txt)
    assert s.format_contract >= 15
    assert s.guardrails >= 10
    assert total(s) > 60
