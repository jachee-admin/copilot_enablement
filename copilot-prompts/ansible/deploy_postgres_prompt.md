
# Prompt: Deploy PostgreSQL 16 on RHEL 9 with Ansible (idempotent, production-ready)

## Goal
Have Copilot generate an **idempotent** Ansible playbook that installs and configures **PostgreSQL 16 on RHEL 9**, initializes the cluster, enables and starts the service, and optionally creates a database and user. The result should be safe, readable, and easy to extend.

## Environment / Constraints (include with the prompt)
- OS: **RHEL 9** (or compatible, e.g., Rocky/Alma 9)
- Use the **official PGDG repo** for PostgreSQL 16
- Use `ansible.builtin.*` modules where possible
- Disable the stock RHEL AppStream `postgresql` module before installing PGDG packages
- Ensure **idempotency** (no needless changes)
- **Handlers** for service restarts on config change
- **Variables** for DB name, user, password, listen address, allowed CIDR
- Secure defaults: **no plaintext secrets in the play** (support `vars_prompt` or extra_vars)
- Optional: create database and role using `community.postgresql` modules (or `become_user: postgres` on vanilla installs)

## Primary Prompt (paste to Copilot)
> Write an idempotent Ansible playbook `deploy_postgres16.yml` for RHEL 9 that:
> 1) Disables the default `postgresql` module and installs the PGDG repo.
> 2) Installs PostgreSQL 16 server and contrib packages.
> 3) Initializes the cluster if not already initialized.
> 4) Configures `postgresql.conf` and `pg_hba.conf` to:
>    - set `listen_addresses` (default `0.0.0.0`)
>    - allow md5 connections from a configurable CIDR (default `10.0.0.0/8`)
> 5) Enables and starts `postgresql-16` via systemd (handler restarts on config change).
> 6) Optionally creates a database and a role/user with password (controlled by vars).
> 7) Uses variables:
>    - `pg_listen: "0.0.0.0"`
>    - `pg_cidr_allow: "10.0.0.0/8"`
>    - `pg_db_name: "metrics"`
>    - `pg_role_name: "metrics_app"`
>    - `pg_role_pass: "CHANGE_ME"`  (allow override via extra_vars)
>    - `pg_create_db: true`
>    - `pg_create_role: true`
> 8) Is fully idempotent, tagged, and easy to lint. Include handlers and task tags. Add notes on psycopg2 dependency for `community.postgresql`.
> Provide a complete playbook with comments and safe defaults.

## Acceptance Criteria
- Disables AppStream `postgresql` module before PGDG install.
- Installs `postgresql16`, `postgresql16-server`, and `postgresql16-contrib`.
- Uses `creates:` guard for initdb idempotency.
- Uses handlers to restart on config changes.
- Safe line edits (or templates) for `postgresql.conf` and `pg_hba.conf`.
- Service **enabled** and **started**.
- Optional DB/user creation obeys `pg_create_db` / `pg_create_role`.
- No secrets hardcoded in the *repo*; support `--extra-vars`.
- Lintable with `ansible-lint`; passes `ansible-playbook --syntax-check`.

## Verification (run these)
```bash
ansible-playbook -i hosts.ini deploy_postgres16.yml --syntax-check
ansible-lint deploy_postgres16.yml
ansible-playbook -i hosts.ini deploy_postgres16.yml -K \
  -e pg_role_pass='S3cr3t!' \
  -e pg_listen='0.0.0.0' \
  -e pg_cidr_allow='10.0.0.0/8'
````

Re-run the play to confirm **changed=0** for idempotent tasks (except handlers triggered by variable changes).

## Notes & Pitfalls

* `community.postgresql` modules may require `python3-psycopg2` on the target.
* For remote DB management, set `login_host`, `login_user`, `login_password`; otherwise use `become_user: postgres` + unix socket.
* Carefully manage firewall rules (not included here by default).
* Prefer templating configs for complex setups; `lineinfile` is fine for small changes.

---

## Reference playbook

```yaml
---
# deploy_postgres16.yml
- name: Deploy PostgreSQL 16 on RHEL 9
  hosts: db
  become: true
  vars:
    pg_listen: "0.0.0.0"
    pg_cidr_allow: "10.0.0.0/8"
    pg_db_name: "metrics"
    pg_role_name: "metrics_app"
    pg_role_pass: "CHANGE_ME"
    pg_create_db: true
    pg_create_role: true

    # Paths for PG 16 on RHEL9 via PGDG
    pg_version: "16"
    pg_service: "postgresql-16"
    pg_bin_dir: "/usr/pgsql-16/bin"
    pg_data_dir: "/var/lib/pgsql/16/data"
    pg_hba: "{{ pg_data_dir }}/pg_hba.conf"
    pg_conf: "{{ pg_data_dir }}/postgresql.conf"

  pre_tasks:
    - name: Ensure dnf-plugins-core (for config-manager) is present
      ansible.builtin.dnf:
        name: dnf-plugins-core
        state: present
      tags: ['packages']

    - name: Disable the AppStream postgresql module
      ansible.builtin.command:
        cmd: dnf -y module disable postgresql
      args:
        creates: /etc/dnf/modules.d/postgresql.module  # best-effort idempotency
      changed_when: false
      tags: ['repo']

    - name: Install PGDG repo
      ansible.builtin.dnf:
        name: https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
        state: present
      tags: ['repo']

  tasks:
    - name: Install PostgreSQL 16 packages
      ansible.builtin.dnf:
        name:
          - postgresql16
          - postgresql16-server
          - postgresql16-contrib
          - python3-psycopg2   # needed for community.postgresql modules
        state: present
      tags: ['packages']

    - name: Initialize database if not initialized
      ansible.builtin.command:
        cmd: "{{ pg_bin_dir }}/postgresql-{{ pg_version }}-setup initdb"
      args:
        creates: "{{ pg_data_dir }}/PG_VERSION"
      notify: Restart PostgreSQL
      tags: ['init']

    - name: Ensure listen_addresses in postgresql.conf
      ansible.builtin.lineinfile:
        path: "{{ pg_conf }}"
        regexp: '^#?\s*listen_addresses\s*='
        line: "listen_addresses = '{{ pg_listen }}'"
        backrefs: false
      notify: Restart PostgreSQL
      tags: ['config']

    - name: Allow md5 connections from CIDR in pg_hba.conf
      ansible.builtin.blockinfile:
        path: "{{ pg_hba }}"
        marker: "# {mark} ANSIBLE MANAGED CIDR ACCESS"
        block: |
          # Allow app clients
          host    all             all             {{ pg_cidr_allow }}         md5
      notify: Restart PostgreSQL
      tags: ['config']

    - name: Enable and start PostgreSQL service
      ansible.builtin.systemd:
        name: "{{ pg_service }}"
        enabled: true
        state: started
      tags: ['service']

    - name: Create database (optional)
      when: pg_create_db | bool
      become_user: postgres
      community.postgresql.postgresql_db:
        name: "{{ pg_db_name }}"
        state: present
      tags: ['db']

    - name: Create role/user (optional)
      when: pg_create_role | bool
      become_user: postgres
      community.postgresql.postgresql_user:
        name: "{{ pg_role_name }}"
        password: "{{ pg_role_pass }}"
        db: "{{ pg_db_name }}"
        priv: "ALL"
        role_attr_flags: "LOGIN"
        state: present
      tags: ['db']

  handlers:
    - name: Restart PostgreSQL
      ansible.builtin.systemd:
        name: "{{ pg_service }}"
        state: restarted
```

### Usage examples

```bash
# Dry run
ansible-playbook -i hosts.ini deploy_postgres16.yml --syntax-check

# First deploy (supply secrets with extra-vars or a vault)
ansible-playbook -i hosts.ini deploy_postgres16.yml -K \
  -e pg_role_pass='S3cureP@ss' \
  -e pg_listen='0.0.0.0' \
  -e pg_cidr_allow='10.0.0.0/8'

# Idempotency check
ansible-playbook -i hosts.ini deploy_postgres16.yml -K -e pg_role_pass='S3cureP@ss'
```

## Follow-up Refinement Prompts

* “Convert `lineinfile`/`blockinfile` to **templates** using `templates/postgresql.conf.j2` and `templates/pg_hba.conf.j2` with variables and comments.”
* “Add **firewalld** tasks to open port 5432 conditionally.”
* “Add **handlers** for `reload` vs `restart` based on changed options.”
* “Support TLS with server cert/key paths and `ssl = on`.”
* “Split into a reusable **role** with defaults and molecule tests.”



