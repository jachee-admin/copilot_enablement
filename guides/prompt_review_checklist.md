# ✅ Prompt Review Checklist

This checklist helps engineers and reviewers validate that Copilot-generated code meets enterprise standards for **security, accuracy, and maintainability**.
Use it during peer review, code scanning, or AI-assisted development audits.

---

## 🧭 1. Prompt Clarity & Scope

| Check | Description | Status |
|--------|--------------|--------|
| 🟩 **Specificity** | Prompt clearly describes the desired output (task, language, framework, version). | ☐ |
| 🟩 **Context** | Includes relevant code snippets, input/output examples, or system info. | ☐ |
| 🟩 **Constraints** | Defines boundaries like performance goals, formatting, style, or compliance needs. | ☐ |
| 🟩 **Role Definition** | Prompt defines the AI’s role (“act as a senior DevOps engineer” or “security auditor”). | ☐ |

**Tip:** A vague prompt = vague code. Clarity cuts hallucination.

---

## 🧰 2. Output Quality & Accuracy

| Check | Description | Status |
|--------|--------------|--------|
| 🟩 **Logic Review** | Output is logically sound and performs the intended task correctly. | ☐ |
| 🟩 **Syntax Validation** | Passes linting or syntax checks. | ☐ |
| 🟩 **Error Handling** | Includes retry, logging, or exception handling where appropriate. | ☐ |
| 🟩 **Documentation** | Comments or docstrings clearly describe function purpose and parameters. | ☐ |
| 🟩 **Idempotency / Repeatability** | Scripts and playbooks can be safely rerun without unintended effects. | ☐ |

---

## 🔒 3. Security & Compliance

| Check | Description | Status |
|--------|--------------|--------|
| 🟩 **No Secrets in Prompts** | No API keys, credentials, or proprietary data were included in the input. | ☐ |
| 🟩 **No Data Leakage** | Output doesn’t expose internal system paths, endpoints, or user data. | ☐ |
| 🟩 **License Check** | No GPL or unapproved license headers copied from Copilot output. | ☐ |
| 🟩 **Dependency Review** | Imported libraries or modules are approved and up to date. | ☐ |

**Policy Reminder:** Treat Copilot as a *public-facing system* — whatever you paste in can theoretically leave your network perimeter.

---

## 🧩 4. Maintainability & Readability

| Check | Description | Status |
|--------|--------------|--------|
| 🟩 **Naming Consistency** | Variable and function names follow org standards. | ☐ |
| 🟩 **Formatting** | Code matches project’s linting and formatting conventions. | ☐ |
| 🟩 **Modularity** | Code broken into small, reusable components. | ☐ |
| 🟩 **Comments** | Inline notes explain *why*, not just *what*. | ☐ |
| 🟩 **Versioning** | AI-generated files are tagged in commits or changelogs. | ☐ |

---

## 📊 5. Performance & Testing

| Check | Description | Status |
|--------|--------------|--------|
| 🟩 **Efficiency** | No obvious performance bottlenecks introduced. | ☐ |
| 🟩 **Test Coverage** | Unit or integration tests accompany generated code. | ☐ |
| 🟩 **Edge Cases Considered** | Prompts or follow-ups include exceptional conditions. | ☐ |
| 🟩 **Regression Safe** | Introduced changes are isolated and reversible. | ☐ |

---

## 🧠 6. Feedback & Iteration

| Step | Purpose | Example |
|------|----------|----------|
| 🔁 **Refine Prompt** | Capture lessons from failed outputs to improve clarity. | “Add parameter validation to user input section.” |
| 📝 **Document Insight** | Record successful prompt patterns in team library. | “Short prompts perform worse for YAML playbooks.” |
| 🗂️ **Version Control** | Commit AI-assisted outputs with meaningful messages. | “Generated with Copilot, reviewed by JH, validated via Ansible-lint.” |

---

## 🏁 Reviewer Notes

| Reviewer | Date | Summary |
|-----------|------|----------|
|  |  |  |

---

**Usage Guidance:**
Keep this checklist near every Copilot-enabled workspace — VS Code, JetBrains, or browser Copilot Chat.
Teams should mark checkboxes before merging AI-generated code into main branches.

> *AI assists productivity, but accountability remains human.*

