Perfect. Let’s make these portfolio artifacts *look* like something Duke Energy (or any large enterprise adopting Copilot) would recognize as immediately useful.
We’ll create practical, professional samples that show:

1. You understand **Copilot prompting**.
2. You can **teach** others how to use it safely and effectively.
3. You think in **frameworks**, not just one-off tricks.

We’ll start with three artifacts that build a cohesive narrative for your portfolio.

---

## Artifact 1 — “Copilot Prompt Playbook for Engineers”

A short markdown or PDF guide meant for internal teams adopting Copilot.

**Filename:** `Copilot_Prompt_Playbook.md`

**Purpose:** Shows your ability to codify prompt-engineering best practices for developers and automation engineers.

**Outline:**

```markdown
# Copilot Prompt Playbook (Engineering Edition)

## Purpose
This playbook helps engineers write clear, repeatable prompts that produce reliable, secure Copilot outputs.

## 1. The 3C Rule
**Clarity, Context, and Constraints**

| Principle | Example |
|------------|----------|
| **Clarity** | ❌ "Write script for deployment"<br>✅ "Write a Bash script to deploy an Nginx container using Docker Compose, logging output to deploy.log" |
| **Context** | Include relevant snippets, function signatures, or comments |
| **Constraints** | Specify output format, coding style, or performance goals |

## 2. Example: Prompting Copilot for Ansible Playbooks
**Prompt:**
> Generate an Ansible playbook that installs PostgreSQL 16 on RHEL9, creates a database named `metrics`, and ensures the service is started on boot.

**Expected Output Review:**
- ✅ Idempotent tasks
- ✅ Uses `become: yes`
- ✅ Includes `handlers`
- ⚠️ Check for hardcoded credentials

## 3. Safe Usage Guidelines
- Never include API keys, secrets, or customer data in prompts.
- Always review generated code for license headers and security implications.
- Treat Copilot output as *draft code*, not production-ready.

## 4. Quick Tips
- Ask for explanations: “Explain this function line by line.”
- Use structured prompts: “Summarize this code in markdown bullets.”
- Iterate and refine: “Now optimize for readability and modularity.”

---
```

This one signals that you understand both Copilot and enterprise governance.

---

## Artifact 2 — “Copilot ROI Tracking Template”

A spreadsheet or markdown template to measure adoption and productivity improvements.

**Filename:** `Copilot_ROI_Template.md`

**Purpose:** Shows your process-oriented side — you don’t just teach Copilot, you measure its impact.

**Example structure:**

```markdown
# Copilot ROI Tracker

| Team | Metric | Baseline | After Copilot | Δ (%) | Notes |
|------|---------|-----------|---------------|-------|-------|
| DevOps | Avg. time to write automation script | 4 hrs | 1.5 hrs | +62% | Significant reduction using standard prompt templates |
| Data Engineering | Bug fix turnaround | 3 days | 2 days | +33% | Faster debugging with “Explain this error” prompts |
| QA | Test coverage | 68% | 78% | +10% | Used Copilot for generating unit tests |
```

Then a short analysis paragraph:

> Teams reported measurable time savings after two weeks of prompt training. Key enablers included internal prompt libraries and standardized review checklists.

---

## Artifact 3 — “Prompt Library for Common Automation Tasks”

This one’s a real crowd-pleaser: a repo folder with categorized prompt examples and sample results.

**Folder:** `copilot-prompts/`

**Sample structure:**

```
copilot-prompts/
├── README.md
├── bash/
│   ├── docker_healthcheck_prompt.md
│   └── log_parser_prompt.md
├── ansible/
│   ├── deploy_postgres_prompt.md
│   ├── user_management_prompt.md
├── python/
│   ├── retry_with_jitter_prompt.md
│   ├── csv_to_json_prompt.md
└── sql/
    ├── audit_trail_trigger_prompt.md
    └── rls_policy_prompt.md
```

Each prompt file should include:

```markdown
# Prompt: Create an Ansible Playbook for User Management

**Prompt:**
> Generate an Ansible playbook that creates a Linux user, assigns it to the `devops` group, ensures idempotency, and logs actions.

**Copilot Output Summary:**
- Creates user if not exists
- Adds to group
- Uses handlers to restart sshd if config changes

**Notes:**
Good initial result. Add task tags, and verify become permissions.
```

This structure demonstrates that you *systematize prompt discovery* — exactly what a Copilot Enablement Lead would be expected to do.

---

If you’d like, next we can generate:

* A **GitHub README.md** layout to tie all these together.
* Or a **case study** artifact (1-pager) describing a “Copilot rollout” you could discuss in interviews.

Which of those should we build next?
