# Copilot Prompts For Common Tasks

## File Structure (per Library)

```text
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

## Example:

# Prompt: Create an Ansible Playbook for User Management

**Prompt:**
> Generate an Ansible playbook that creates a Linux user, assigns it to the `devops` group, ensures idempotency, and logs actions.

**Copilot Output Summary:**
- Creates user if not exists
- Adds to group
- Uses handlers to restart sshd if config changes

**Notes:**
Good initial result. Add task tags, and verify become permissions.
