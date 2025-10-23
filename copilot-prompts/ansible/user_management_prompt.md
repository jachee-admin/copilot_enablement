# Prompt: Linux User Management with Ansible (idempotent, secure)

## Goal
Generate an idempotent Ansible playbook that creates and manages **Linux users** and groups safely.
The playbook should handle user creation, group assignment, SSH key setup, and removal when needed.

## Context / Constraints
- OS: RHEL 8+ / Rocky / Alma / Ubuntu (generic Linux)
- Use only **ansible.builtin** modules — no shell commands.
- Must be **idempotent** (running twice changes nothing).
- Support managing multiple users through variables.
- Store authorized SSH keys in `/home/{{ user }}/.ssh/authorized_keys`.
- Enforce secure permissions on `.ssh` directories and keys.
- Allow configurable options per user: shell, groups, sudo access, state (present/absent).
- No hardcoded passwords; allow them via `--extra-vars` or encrypted vaults.

## Primary Prompt (for Copilot)
> Write an idempotent Ansible playbook named `user_management.yml` that manages Linux user accounts using a variable list `users`.
> For each user, create the account, primary group, optional secondary groups, and configure SSH authorized keys.
> Requirements:
> - Use `ansible.builtin.user` and `ansible.builtin.authorized_key`.
> - Support keys as inline strings or file paths.
> - Handle sudo privilege by adding user to `wheel` or `sudo`.
> - Enforce 700 perms on `.ssh`, 600 on authorized_keys.
> - Make the playbook idempotent.
>+ Example vars:
>   ```yaml
>   users:
>     - name: deploy
>       groups: ['devops']
>       shell: /bin/bash
>       state: present
>       sudo: true
>       ssh_keys:
>         - "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBexample1 user@laptop"
>     - name: tempuser
>       state: absent
>    ```





## Acceptance Criteria
- Idempotent on re-run.
- Proper permissions on all created directories/files.
- Supports both adding and removing users.
- Handles multiple SSH keys per user.
- Clean and lintable (`ansible-lint` passes).
- No plaintext passwords or unsafe commands.

---

## Reference playbook
```yaml
---
# user_management.yml
- name: Manage system users and SSH keys
  hosts: all
  become: true
  vars:
    users: []

  tasks:
    - name: "Ensure user groups exist"
      ansible.builtin.group:
        name: "{{ item.groups | default([]) | first | default(item.name) }}"
        state: present
      loop: "{{ users | selectattr('state', 'defined') | selectattr('state', 'equalto', 'present') | list }}"
      loop_control:
        label: "{{ item.name }}"
      tags: ['groups']

    - name: "Manage user accounts"
      ansible.builtin.user:
        name: "{{ item.name }}"
        shell: "{{ item.shell | default('/bin/bash') }}"
        groups: "{{ item.groups | default([]) | join(',') }}"
        append: yes
        state: "{{ item.state | default('present') }}"
      loop: "{{ users }}"
      loop_control:
        label: "{{ item.name }}"
      tags: ['users']

    - name: "Configure sudo privileges"
      ansible.builtin.lineinfile:
        path: /etc/sudoers.d/{{ item.name }}
        line: "{{ item.name }} ALL=(ALL) NOPASSWD:ALL"
        create: yes
        mode: '0440'
        owner: root
        group: root
      when: item.sudo | default(false)
      loop: "{{ users | selectattr('state', 'equalto', 'present') | list }}"
      tags: ['sudo']

    - name: "Remove sudoers file for deleted users"
      ansible.builtin.file:
        path: /etc/sudoers.d/{{ item.name }}
        state: absent
      when: item.state | default('present') == 'absent'
      loop: "{{ users }}"
      tags: ['sudo']

    - name: "Setup .ssh directory"
      ansible.builtin.file:
        path: "/home/{{ item.name }}/.ssh"
        state: directory
        mode: '0700'
        owner: "{{ item.name }}"
        group: "{{ item.name }}"
      when:
        - item.state | default('present') == 'present'
        - item.ssh_keys is defined
      loop: "{{ users }}"
      tags: ['ssh']

    - name: "Deploy authorized keys"
      ansible.builtin.authorized_key:
        user: "{{ item.name }}"
        key: "{{ ssh_key }}"
        state: present
      vars:
        ssh_key: "{{ key }}"
      loop: "{{ users | selectattr('state', 'equalto', 'present') | list }}"
      loop_control:
        label: "{{ item.name }}"
      with_items: "{{ item.ssh_keys | default([]) }}"
      when: item.ssh_keys is defined
      tags: ['ssh']

    - name: "Ensure ownership and permissions"
      ansible.builtin.file:
        path: "/home/{{ item.name }}/.ssh/authorized_keys"
        owner: "{{ item.name }}"
        group: "{{ item.name }}"
        mode: '0600'
      when: item.ssh_keys is defined and item.state | default('present') == 'present'
      loop: "{{ users }}"
      tags: ['ssh']
```
### Example vars file (group_vars/all.yml)
```yaml
users:
  - name: deploy
    groups: ['devops']
    shell: /bin/bash
    sudo: true
    state: present
    ssh_keys:
      - "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBexample1 user@laptop"

  - name: tempuser
    state: absent
```

---

### Testing
```bash
ansible-playbook -i inventory user_management.yml --syntax-check
ansible-lint user_management.yml
ansible-playbook -i inventory user_management.yml -K
```
Re-run to confirm idempotency (should return changed=0).

### Follow-up Refinement Prompts

- “Add support for password-based users using user.password (hashed).”
- “Move users into a reusable Ansible role with defaults/main.yml and templates.”
- “Add Molecule tests to verify permissions and key deployment.”
- “Integrate with LDAP or SSSD for hybrid environments.”
- “Add handler to reload SSH daemon when authorized keys change.”