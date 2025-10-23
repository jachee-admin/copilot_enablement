# Prompt: Log Parser (Bash + awk/sed/grep, resilient & reusable)

## Goal
Generate a Bash utility script that parses structured or semi-structured logs (e.g., system, app, web logs) and produces useful summaries — counts, error breakdowns, and response-time stats — using only **standard Unix tools**.

## Context / Constraints
- Must work on Linux/macOS with `/usr/bin/env bash`.
- Input log examples (any similar format):
```
2025-10-23 10:22:01 [INFO] Service started
2025-10-23 10:22:05 [WARN] Slow response: 420ms /api/health
2025-10-23 10:22:09 [ERROR] DB timeout /api/login user=john
2025-10-23 10:22:14 [INFO] Request completed: 210ms /api/login user=jane
```
- The parser should:
- Print **summary counts** (INFO/WARN/ERROR totals)
- Extract **top 5 endpoints** by count
- Compute **average response time** (lines with `ms`)
- Support optional filtering:
  - `--level ERROR` → only errors
  - `--since "2025-10-23 10:22:05"` → ignore older lines
  - `--endpoint /api/login` → filter endpoint substring
- Handle missing fields gracefully (no crash).
- Produce human-readable output with aligned columns.
- No dependencies beyond POSIX + `awk`, `grep`, `sed`, `date`, `sort`, `uniq`.
- Should exit non-zero on invalid args or missing input file.

---

## Primary Prompt (for Copilot)
> Write a portable Bash script `log_parser.sh` that:
> - Accepts arguments: `--file`, `--level`, `--since`, `--endpoint`.
> - Parses timestamps, levels, response times (ms), and endpoints.
> - Prints a summary:
>   ```
>   Level Counts:
>     INFO:  20
>     WARN:  5
>     ERROR: 2
>
>   Top Endpoints:
>     /api/login      10
>     /api/health     7
>
>   Avg Response Time: 245 ms
>   ```
> - Use `awk` for structured parsing, `grep/sort/uniq` for counting.
> - Ignore lines older than `--since` (parse timestamps with GNU `date -d`).
> - Gracefully skip missing `ms` values.
> - Exit with non-zero status on argument errors or unreadable file.
> - Include inline comments for readability.

---

## Acceptance Criteria
- Works with logs in `YYYY-MM-DD HH:MM:SS [LEVEL] message` format.
- Handles missing `ms` lines (skip safely).
- Filters correctly by level, endpoint, and since-time.
- Produces aligned, readable output.
- Lintable via `shellcheck`.

---

## Reference Script

```bash
#!/usr/bin/env bash
# log_parser.sh — lightweight log summarizer
# Usage:
#   ./log_parser.sh --file app.log [--level ERROR] [--since "2025-10-23 10:00:00"] [--endpoint /api/login]

set -euo pipefail

# --- Parse args ---
LEVEL_FILTER=""
SINCE_FILTER=""
ENDPOINT_FILTER=""
LOG_FILE=""

while [[ $# -gt 0 ]]; do
case "$1" in
  --file) LOG_FILE="$2"; shift 2 ;;
  --level) LEVEL_FILTER="$2"; shift 2 ;;
  --since) SINCE_FILTER="$2"; shift 2 ;;
  --endpoint) ENDPOINT_FILTER="$2"; shift 2 ;;
  -h|--help)
    echo "Usage: $0 --file app.log [--level LEVEL] [--since 'YYYY-MM-DD HH:MM:SS'] [--endpoint /api/...]" >&2
    exit 0 ;;
  *) echo "Unknown arg: $1" >&2; exit 1 ;;
esac
done

[[ -f "$LOG_FILE" ]] || { echo "Error: file not found: $LOG_FILE" >&2; exit 1; }

# --- Time cutoff ---
if [[ -n "$SINCE_FILTER" ]]; then
SINCE_EPOCH=$(date -d "$SINCE_FILTER" +%s 2>/dev/null || :)
if [[ -z "${SINCE_EPOCH:-}" ]]; then
  echo "Invalid --since timestamp" >&2; exit 1
fi
fi

# --- Apply filters ---
FILTERED=$(mktemp)
trap 'rm -f "$FILTERED"' EXIT

awk -v lvl="$LEVEL_FILTER" -v ep="$ENDPOINT_FILTER" -v since="${SINCE_EPOCH:-0}" '
function parse_ts(ts, t, cmd, epoch) {
cmd = "date -d \"" ts "\" +%s"
cmd | getline epoch
close(cmd)
return epoch
}
{
ts = $1 " " $2
level = gensub(/.*\[(.+)\].*/, "\\1", "g")
if (lvl && level != lvl) next
if (ep && index($0, ep) == 0) next
if (since) {
  epoch = parse_ts(ts)
  if (epoch < since) next
}
print
}' "$LOG_FILE" > "$FILTERED"

# --- Summaries ---
echo "Level Counts:"
awk '
match($0, /\[(INFO|WARN|ERROR)\]/, m) { c[m[1]]++ }
END { printf "  INFO:  %d\n  WARN:  %d\n  ERROR: %d\n", c["INFO"], c["WARN"], c["ERROR"] }
' "$FILTERED"

echo
echo "Top Endpoints:"
grep -oE '/api/[A-Za-z0-9_/-]+' "$FILTERED" | sort | uniq -c | sort -nr | head -5 | awk '{printf "  %-15s %s\n", $2, $1}'

echo
echo "Avg Response Time:"
awk '
match($0, /([0-9]+)ms/, m) { sum += m[1]; n++ }
END {
  if (n > 0) printf "  %.1f ms\n", sum / n;
  else print "  (no response times found)"
}
' "$FILTERED"
```

### Example Run
```bash
chmod +x log_parser.sh
./log_parser.sh --file app.log --level ERROR --since "2025-10-23 10:22:00"
```

#### Output:
```bash
Level Counts:
  INFO:  0
  WARN:  0
  ERROR: 1

Top Endpoints:
  /api/login       1

Avg Response Time:
  (no response times found)
```
### Notes & Pitfalls

- Performance: For massive logs, pipe through awk directly without grep | awk | sort chains.
- Time parsing: date -d is GNU-specific; on macOS use gdate (coreutils).
- Escaping: When filtering endpoints containing ? or &, quote --endpoint properly.
- Future refinement: Support JSON logs with jq, or add histogram of response times.

### Follow-up Refinement Prompts

- “Add color highlighting for ERROR/WARN using tput.”
- “Add --json flag to emit machine-readable summary.”
- “Add --tail mode (stream log, refresh summary every N seconds).”
- “Extend awk logic to group by hour or endpoint automatically.”
- “Add --pattern 'regex' filter for arbitrary matching.”