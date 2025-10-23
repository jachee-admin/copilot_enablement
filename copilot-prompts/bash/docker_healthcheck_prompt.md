# Prompt: Docker Health Monitor (Bash) — inspect, report, auto-restart

## Goal
Generate a portable **Bash** utility that inspects Docker containers’ **HEALTHCHECK** status, prints a readable report, and (optionally) **restarts** containers that are `unhealthy`, with a bounded retry + grace wait.

## Context / Constraints (include with the prompt)
- OS: Linux/macOS with `/usr/bin/env bash`.
- Dependencies: `docker` CLI; **no jq required** (use `docker inspect --format`).
- Support selecting containers by:
  - `--name <container>` (repeatable)
  - `--label <key=val>` (filter set)
  - `--all` (default: only running containers)
- Health logic:
  - Read `.State.Health.Status` (values: `healthy`, `starting`, `unhealthy`).
  - Containers **without** a HEALTHCHECK are reported as `no-healthcheck`.
- Optional actions:
  - `--restart-unhealthy` → `docker restart` any `unhealthy` container.
  - `--grace <seconds>` → after restart, wait and re-check (default 10).
  - `--max-retries <n>` → try up to N restarts per container (default 2).
- Output: Table listing **NAME**, **STATUS**, **HEALTH**, **EXITCODE**, **LASTCHECK**.
- Exit codes:
  - `0` if all are `healthy` or `no-healthcheck`
  - `1` if any `unhealthy` and not restarted (or still unhealthy after retries)
  - `2` on usage/argument errors
- Script must be **shellcheck**-friendly, `set -euo pipefail`.

## Primary Prompt (paste to Copilot)
> Write `docker_healthcheck.sh` that:
> - Parses args: `--name`, `--label`, `--all`, `--restart-unhealthy`, `--grace N`, `--max-retries N`, `--help`.
> - Builds the candidate container list via `docker ps` (with `--filter label=...` and `--format '{{.Names}}'`), or uses explicit `--name` values.
> - For each container, fetch fields via `docker inspect --format`:
>   - `.Name` (trim leading slash)
>   - `.State.Status` (running/exited)
>   - `.State.Health.Status` (or empty)
>   - `.State.Health.Log[-1].ExitCode` (if present)
>   - `.State.Health.Log[-1].End` (timestamp)
> - Compute a `HEALTH` column:
>   - if health empty → `no-healthcheck`
>   - else `healthy|starting|unhealthy`
> - When `--restart-unhealthy` is set:
>   - For each `unhealthy` container, up to `--max-retries`, do:
>     - `docker restart <name>`
>     - sleep `--grace` seconds
>     - re-inspect health; stop early if healthy
> - Print a table. Return `0` if all healthy/no-healthcheck; otherwise `1`.
> - Be robust to containers exiting or disappearing mid-run.
> - Include inline comments and a usage header.

## Acceptance Criteria
- No `jq` usage; only `docker` templates and Bash.
- Works when no containers match (prints message; exit 0).
- Doesn’t crash if `.State.Health` is missing.
- Bounded restart attempts and grace wait are honored.
- Clear, column-aligned report.

---

## Reference Script

```bash
#!/usr/bin/env bash
# docker_healthcheck.sh — Inspect and (optionally) auto-heal Docker containers
# Usage:
#   ./docker_healthcheck.sh [--name web] [--label app=api] [--all] \
#     [--restart-unhealthy] [--grace 10] [--max-retries 2]
#
# Exit codes:
#   0 = all containers healthy or no-healthcheck
#   1 = at least one unhealthy (and not recovered)
#   2 = usage/argument error

set -euo pipefail

NAMES=()
LABELS=()
ALL=false
RESTART=false
GRACE=10
MAX_RETRIES=2

err() { printf "error: %s\n" "$*" >&2; }
usage() {
  grep -E '^# ' "$0" | sed 's/^# //'
}

while [[ $# -gt 0 ]]; do
  case "${1:-}" in
    --name) NAMES+=("$2"); shift 2 ;;
    --label) LABELS+=("$2"); shift 2 ;;
    --all) ALL=true; shift ;;
    --restart-unhealthy) RESTART=true; shift ;;
    --grace) GRACE="${2:-}"; shift 2 ;;
    --max-retries) MAX_RETRIES="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) err "unknown arg: $1"; usage; exit 2 ;;
  esac
done

# Validate numbers
[[ "$GRACE" =~ ^[0-9]+$ ]] || { err "--grace must be integer seconds"; exit 2; }
[[ "$MAX_RETRIES" =~ ^[0-9]+$ ]] || { err "--max-retries must be integer"; exit 2; }

# Build candidate list
list_containers() {
  local args=()
  if $ALL; then
    args+=( -a )
  fi
  for l in "${LABELS[@]:-}"; do
    args+=( --filter "label=$l" )
  done
  docker ps "${args[@]}" --format '{{.Names}}'
}

# Merge explicit names (dedupe)
declare -A seen=()
CANDIDATES=()

if [[ "${#NAMES[@]}" -gt 0 ]]; then
  for n in "${NAMES[@]}"; do
    if [[ -n "${seen[$n]:-}" ]]; then continue; fi
    CANDIDATES+=("$n"); seen[$n]=1
  done
fi

while IFS= read -r n; do
  [[ -z "$n" ]] && continue
  if [[ -z "${seen[$n]:-}" ]]; then
    CANDIDATES+=("$n"); seen[$n]=1
  fi
done < <(list_containers || true)

if [[ "${#CANDIDATES[@]}" -eq 0 ]]; then
  echo "No matching containers."
  exit 0
fi

# Helpers to inspect safely
inspect() {
  local name="$1" fmt="$2"
  docker inspect --format "$fmt" "$name" 2>/dev/null || true
}

trimslash() { sed 's#^/##'; }

printf "%-25s %-10s %-15s %-9s %s\n" "NAME" "STATE" "HEALTH" "EXITCODE" "LASTCHECK"
printf "%-25s %-10s %-15s %-9s %s\n" "-------------------------" "----------" "---------------" "---------" "---------------------------"

UNHEALTHY=0

recheck_health() {
  local name="$1"
  local health
  health="$(inspect "$name" '{{if .State.Health}}{{.State.Health.Status}}{{end}}')"
  if [[ -z "$health" ]]; then
    echo "no-healthcheck"
  else
    echo "$health"
  fi
}

for c in "${CANDIDATES[@]}"; do
  # Fetch fields
  NAME="$(inspect "$c" '{{.Name}}' | trimslash)"
  [[ -z "$NAME" ]] && NAME="$c"

  STATE="$(inspect "$c" '{{.State.Status}}')"
  HEALTH="$(recheck_health "$c")"
  EXITCODE="$(inspect "$c" '{{if .State.Health}}{{(index .State.Health.Log (sub (len .State.Health.Log) 1)).ExitCode}}{{end}}')"
  LASTCHECK="$(inspect "$c" '{{if .State.Health}}{{(index .State.Health.Log (sub (len .State.Health.Log) 1)).End}}{{end}}')"

  printf "%-25s %-10s %-15s %-9s %s\n" "$NAME" "${STATE:-?}" "${HEALTH:-?}" "${EXITCODE:-}" "${LASTCHECK:-}"

  if [[ "$HEALTH" == "unhealthy" ]]; then
    UNHEALTHY=$((UNHEALTHY+1))

    if $RESTART; then
      tries=0
      while [[ $tries -lt $MAX_RETRIES ]]; do
        echo "Restarting $NAME (attempt $((tries+1))/$MAX_RETRIES) ..."
        docker restart "$NAME" >/dev/null || true
        sleep "$GRACE"
        HEALTH="$(recheck_health "$NAME")"
        echo "  → post-restart health: $HEALTH"
        if [[ "$HEALTH" == "healthy" ]]; then
          UNHEALTHY=$((UNHEALTHY-1))
          break
        fi
        tries=$((tries+1))
      done
    fi
  fi
done

if [[ $UNHEALTHY -gt 0 ]]; then
  exit 1
fi
exit 0
```

### Example runs
```bash
# Inspect running containers with label filter
./docker_healthcheck.sh --label com.example.stack=prod

# Include stopped containers too
./docker_healthcheck.sh --all

# Target specific containers by name
./docker_healthcheck.sh --name api --name worker

# Auto-restart unhealthy ones, wait 15s after restart, up to 3 retries
./docker_healthcheck.sh --restart-unhealthy --grace 15 --max-retries 3
```

### *Bonus: how to define a robust HEALTHCHECK*

Include a snippet in your repo so teams remember to add meaningful checks.

#### Dockerfile
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://localhost:8080/health || exit 1
```

### docker-compose.yml
```yaml
services:
  api:
    image: myorg/api:latest
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s
    labels:
      com.example.stack: "prod"
```

### Notes & Pitfalls
- The script treats no HEALTHCHECK as no-healthcheck (neutral). Add checks to critical services.
- On macOS, Docker Desktop can lag health updates. Use a slightly longer --grace.
- If your health command is expensive, increase start_period to avoid flapping.
- For fleets, run this under cron or as a sidecar with --restart-unhealthy.

### Follow-up Refinement Prompts
- “Add --json output mode for machine-readable status.”
- “Add Slack/Webhook notifications when restarts happen.”
- “Track restart counts via a local state file to avoid restart storms.”
- “Add a whitelist/blacklist file to exclude certain containers.”