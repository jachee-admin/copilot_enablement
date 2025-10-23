# Prompt: CSV → JSON Converter (grouping, schema hints, CLI)

## Goal
Have Copilot generate a small, production-ready Python tool that converts a CSV file to JSON with optional **grouping by a column**, **type coercion**, and a clean **CLI**. It should stream safely (no huge memory spikes), handle UTF-8 cleanly, and be easy to test.

## Context / Constraints (include with the prompt)
- Python **3.10+**, **standard library only** (csv, json, argparse, pathlib, typing).
- **UTF-8** read/write. Handle Windows newlines gracefully.
- Options:
  - `--group-by <col>` → output object keyed by that column (values are arrays of rows).
  - `--array` (default) → output an array of row dicts (no grouping).
  - `--infer-types` → coerce ints/floats/bools/nulls when obvious.
  - `--limit N` → only process first N rows (useful for previews).
  - `--indent N` → pretty printing (default 2).
  - `--select col1,col2,...` → project subset of columns.
- On header mismatch or missing `--group-by` column, **exit with non-zero** and a clear message.
- Treat empty strings as `null` **only when `--infer-types` is enabled**.
- Streaming approach: iterate `csv.DictReader`, write out progressively; if `--group-by` is used, aggregate in a `defaultdict(list)`.
- Provide **type hints**, docstrings, and small, testable helpers.
- No third-party libs.

## Primary Prompt (paste to Copilot)
> Write a Python module `csv_to_json.py` that converts CSV to JSON with CLI options:
> - `--input`, `--output`, `--group-by`, `--array` (default), `--infer-types`, `--limit`, `--indent`, `--select`.
> - UTF-8 I/O; newline handling on Windows.
> - When `--group-by` is set, emit `{key: [rows...]}` JSON; otherwise emit `[rows...]`.
> - Implement `infer_value(s: str) -> Any` used only when `--infer-types` is set:
>   - int, float, bool (`true`/`false` case-insensitive), null (`""`, `"null"`), otherwise original string.
> - Validate that `--group-by` exists in headers; error if not.
> - If `--select` is provided, keep only those columns (error on unknown column).
> - Include `main()` with argparse, logging to stderr for warnings/errors, and proper exit codes.
> - Provide small unit-testable helpers and docstrings. Standard library only.

## Acceptance Criteria
- CLI works with both array mode and group-by mode.
- `--infer-types` performs conservative coercion (no surprises).
- Meaningful errors for bad headers / missing columns.
- Deterministic output ordering for keys/columns (preserve CSV header order).
- Handles large files without loading entire file into memory in array mode (streamed write).
- Re-runnable; no side effects beyond output file.

---

## Reference Script (reference implementation)

```python
# csv_to_json.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence
import argparse
import csv
import json
import sys
import io
from collections import defaultdict

def infer_value(s: str) -> Any:
    """Conservatively coerce a CSV string to int/float/bool/null when obvious."""
    t = s.strip()
    if t == "":
        return None
    low = t.lower()
    if low in {"true", "false"}:
        return low == "true"
    if low == "null":
        return None
    # int?
    if t.isdigit() or (t.startswith("-") and t[1:].isdigit()):
        try:
            return int(t)
        except ValueError:
            pass
    # float?
    try:
        # Avoid int-like strings turning into floats by checking above first
        return float(t)
    except ValueError:
        pass
    return s

def project_row(row: dict[str, str], keep: Sequence[str]) -> dict[str, str]:
    return {k: row[k] for k in keep}

def validate_headers(headers: Sequence[str], required: Iterable[str]) -> None:
    unknown = [c for c in required if c not in headers]
    if unknown:
        raise SystemExit(f"Unknown column(s): {', '.join(unknown)}")

def write_json_array(rows: Iterator[dict[str, Any]], out_fp: io.TextIOBase, indent: int | None) -> None:
    """Stream rows as a JSON array without holding all rows in memory."""
    out_fp.write("[")
    first = True
    for row in rows:
        if not first:
            out_fp.write(",")
        else:
            first = False
        if indent:
            out_fp.write("\n" + " " * 2)
        json.dump(row, out_fp, ensure_ascii=False)
    if indent:
        out_fp.write("\n")
    out_fp.write("]")

def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CSV → JSON converter with grouping and type inference.")
    p.add_argument("--input", "-i", type=Path, required=True, help="Input CSV file path")
    p.add_argument("--output", "-o", type=Path, required=True, help="Output JSON file path")
    p.add_argument("--group-by", "-g", type=str, help="Column to group by (emits {key: [rows...]})")
    p.add_argument("--array", action="store_true", help="Emit JSON array (default if --group-by not set)")
    p.add_argument("--infer-types", action="store_true", help="Coerce ints/floats/bools/null when obvious")
    p.add_argument("--limit", type=int, help="Process only first N data rows")
    p.add_argument("--indent", type=int, default=2, help="JSON indent; 0 for compact")
    p.add_argument("--select", type=str, help="Comma-separated list of columns to keep")
    return p.parse_args(argv)

def run(argv: Sequence[str]) -> int:
    ns = parse_args(argv)
    indent = None if ns.indent == 0 else ns.indent

    # Open files with explicit UTF-8 and newline handling
    with ns.input.open("r", encoding="utf-8", newline="") as f_in, \
         ns.output.open("w", encoding="utf-8", newline="") as f_out:

        reader = csv.DictReader(f_in)
        if reader.fieldnames is None:
            raise SystemExit("CSV appears to have no header row.")

        headers = reader.fieldnames

        # Select projection
        select_cols: list[str] | None = None
        if ns.select:
            select_cols = [c.strip() for c in ns.select.split(",") if c.strip()]
            validate_headers(headers, select_cols)

        # Validate group-by column
        if ns.group_by:
            validate_headers(headers, [ns.group_by])

        # Row iterator with optional projection and inference
        def row_iter() -> Iterator[dict[str, Any]]:
            count = 0
            for row in reader:
                if select_cols:
                    row = project_row(row, select_cols)
                if ns.infer_types:
                    row = {k: infer_value(v) for k, v in row.items()}
                if ns.limit is not None and count >= ns.limit:
                    break
                count += 1
                yield row

        if ns.group_by:
            # Aggregate in memory by key (reasonable for moderate distinct keys)
            grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
            key = ns.group_by
            for r in row_iter():
                k = r.get(key)
                if k is None:
                    # Keep behavior predictable: treat missing key as "null" bucket
                    k = "null"
                grouped[str(k)].append(r)
            json.dump(grouped, f_out, indent=indent, ensure_ascii=False)
        else:
            write_json_array(row_iter(), f_out, indent)

    return 0

def main() -> None:
    try:
        sys.exit(run(sys.argv[1:]))
    except SystemExit as e:
        # argparse already printed; ensure non-zero codes bubble
        raise
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
```

### Usage
```bash
# Array mode (default)
python csv_to_json.py --input data.csv --output data.json

# Group by a column, infer types, select a subset of columns, pretty print
python csv_to_json.py -i data.csv -o data_by_cat.json \
  --group-by category --infer-types --select id,category,amount --indent 2

# Compact output, preview first 100 rows
python csv_to_json.py -i data.csv -o preview.json --limit 100 --indent 0
```

### Quick Tests
```bash
# 1) Missing header → error
python csv_to_json.py -i /dev/null -o out.json || echo "PASS (no header)"

# 2) Unknown group-by → error
python csv_to_json.py -i data.csv -o out.json --group-by nope && echo "FAIL" || echo "PASS"

# 3) Streaming array (large file) — should not explode RAM
python csv_to_json.py -i big.csv -o big.json

# 4) Type inference spot-check
printf 'a,b\n1,TRUE\n2,\n' > t.csv
python csv_to_json.py -i t.csv -o t.json --infer-types
cat t.json  # expect [{"a":1,"b":true},{"a":2,"b":null}]
```

### Notes & Pitfalls

- Grouping accumulates rows per key; if you have millions of distinct keys, switch to a “chunked write per key” strategy.
- CSVs with duplicated headers are ambiguous; csv.DictReader keeps last occurrence—document expectations internally.
- Keep ensure_ascii=False to preserve Unicode. Consumers should read as UTF-8.

### Follow-up Refinement Prompts

- “Add a mode that writes one JSON file per group key into an output directory.”
- “Add schema declaration (YAML) to force certain columns to int/float/bool/date.”
- “Add date/time parsing with datetime.fromisoformat when --infer-types is on.”
- “Add a stats subcommand that prints row count, distinct keys, and null ratios.”