
# Copilot Common Prompt Patterns
Short, reusable blocks for Copilot Chat (VS Code/JetBrains), GitHub Copilot, and M365 Copilot. Mix and match. Each block emphasizes **clarity**, **safety**, and **verifiability**.

> *Treat prompts like code: version them, review them, and keep a change log.*

---

## 0) Quick Usage Template
```text
[ROLE SETUP]
[CONTEXT] (what we’re doing, tech stack, constraints)
[TASK] (single, specific ask)
[FORMAT CONTRACT] (exact output shape)
[GUARDRAILS] (don’t guess; how to verify unknowns)
[ACCEPTANCE] (bulleted checks)
````

Example:

```text
Act as a senior Ansible reviewer.
Context: RHEL9, deploy Postgres 16 via PGDG repo.
Task: Write an idempotent playbook with handlers and optional DB/user creation.
Format: Respond only with YAML keys: version, tasks, handlers, vars, notes.
Guardrails: Do not fabricate package names; if uncertain, say "not sure" and suggest 1–3 commands to verify.
Acceptance: disables AppStream module, uses ansible.builtin.*, idempotent initdb, handlers on config change, passes ansible-lint.
```

---

## 1) Role Setup (Context Primers)

### Ansible Reviewer (strict, idempotent)

```text
Act as a senior Ansible reviewer.
Priorities: idempotency, handlers on config change, ansible.builtin.* over shell, tags, lint-clean.
Output must cite risky assumptions as a bulleted list before the final answer.
```

### Python SRE (robustness & tests)

```text
Act as a senior Python SRE.
Standards: type hints, small pure functions, argparse CLI, logging, safe file I/O, graceful errors.
Deliverables: code and a minimal pytest covering happy path + one edge case.
```

### SQL/PostgreSQL DBA (safety first)

```text
Act as a PostgreSQL DBA.
Rules: schema-qualify objects, IF NOT EXISTS, transactions, RLS-aware, indexes for filters.
Include EXPLAIN advice and rollback notes when DDL alters existing data.
```

### Security Auditor (governance)

```text
Act as a security reviewer.
Check for secrets, license issues, dependency risks, and data leakage.
Output: risks[], mitigations[], and a one-paragraph summary.
```

### M365 Copilot Knowledge Worker

```text
Act as a concise business writer.
Constraints: no PII beyond provided text, bullets over prose, action items first, ≤ 150 words unless asked.
```

---

## 2) Format Contracts (Output Specifications)

### YAML Only (fixed keys)

```text
Respond only with YAML using these keys:
version: <semver>
goals: [ ... ]
steps: [ ... ]        # imperative steps (1 line each)
risks: [ ... ]        # concrete, testable risks
validation: [ ... ]   # commands/checks I can run
```

### JSON Contract (schema hint)

```text
Respond only with JSON matching this shape:
{
  "summary": "string",
  "actions": ["string", "..."],
  "risks": ["string", "..."]
}
No prose outside JSON.
```

### Code Only

```text
Output code only — no commentary, headers, or backticks. If context is missing, emit TODO stubs where needed.
```

### Markdown Table

```text
Produce a markdown table with columns:
| Step | Command | Expected Outcome | Rollback |
No extra text above or below the table.
```

---

## 3) Guardrails (Safety & Anti-Hallucination)

### Don’t fabricate + verification path

```text
Do not fabricate package names, APIs, or module options.
If unknown, reply "not sure" and propose 1–3 verification commands (e.g., apt-cache/pip search/ansible-doc/psql \df).
```

### Sensitive data discipline

```text
Never include real secrets or PII. Use placeholders like ${DB_PASSWORD}. If a value looks sensitive, replace with <REDACTED> and note it.
```

### Licensing

```text
Flag potential license conflicts if code resembles known projects; suggest attribution or alternative implementation.
```

### Safe vs fast paths

```text
If a faster but riskier option exists, present both clearly:
[safe_default]: ...
[fast_path]: ...
State trade-offs in one sentence each.
```

---

## 4) Verification Patterns (Prove it Works)

### Terminal checks

```text
Add a "Verification" block with commands I can run now.
Include: setup, the check, expected cues, and cleanup.
```

### Python tests (pytest)

```text
Include a minimal pytest: one happy path + one edge case; no external services (use fakes/tempfiles).
```

### Ansible

```text
Footer must include:
- ansible-playbook --syntax-check <file>
- ansible-lint <file>
- Re-run idempotency note: expect changed=0 on second run
```

### PostgreSQL

```text
Wrap DDL in a transaction; include EXPLAIN for key queries; note required indexes and lock considerations.
```

---

## 5) Iteration & Critique Loops

### Self-critique → improve

```text
Before the final answer, list 3 self-critique bullets (risks, clarity, testability).
Then provide the improved version only.
```

### Diff-only patch

```text
Show only a unified diff from the previous version (no commentary).
```

---

## 6) Domain Starters (Copy/Paste)

### Ansible role skeleton

```text
Create a minimal idempotent Ansible role:
- tasks/main.yml
- handlers/main.yml
- defaults/main.yml
Standards: ansible.builtin.*, handlers on change, variables not hardcoded, tags present.
```

### Python CLI skeleton

```text
Create a standard-library-only CLI with argparse + logging + exit codes.
Include main() guard, usage docstring, and a --version flag.
```

### Bash script (guarded)

```text
Create a portable bash script with: `set -euo pipefail`, getopts parsing, help text, and trap cleanup.
```

### PostgreSQL RLS template

```text
Enable RLS on <schema.table>; create USING and WITH CHECK policies tied to function app.tenant_id().
Include an index on tenant_id and a short demo of allowed/denied operations.
```

---

## 7) Troubleshooting Prompts

### Minimal repro

```text
Reduce to the smallest failing snippet; provide input, expected, actual, environment. Then fix with a single focused change.
```

### On-call style

```text
Give a 30-second diagnosis, likely root cause, and the first two commands to run. Keep it actionable.
```

---

## 8) Review Checklists (Micro)

### Language-agnostic micro-review

```text
Checklist: correctness, naming, complexity, errors/edge cases, logs, tests, docs, dependency risk.
Output pass/fail per item + one-line fix hints.
```

### Ansible micro-review

```text
Checklist: idempotency, module vs shell, handlers, vars, tags, lint, security (no world-writable), notify triggers.
```

---

## 9) Retrieval & Context Packing

```text
Before answering, summarize key facts from the provided context in 3 bullets (no external assumptions). Then answer with the requested format.
```

---

## 10) “Prompt Sandwich” (strong default)

```text
You are [ROLE]. Follow the standards below.
Context: [stack, versions, constraints]
Task: [single clear outcome]
Output: [format contract]
Guardrails: [do-not-guess; verification commands]
Acceptance: [bulleted checks the output must pass]
```

```

Want me to slot this into the repo and tweak your README to link to these sections?
```
