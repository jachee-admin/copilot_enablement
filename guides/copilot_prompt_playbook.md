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
