#!/usr/bin/env python
import sys, json, argparse, pathlib
from coach.scorer import score_and_improve

def main():
    ap = argparse.ArgumentParser(description="Prompt Coach (AI Prompt Optimizer)")
    ap.add_argument("--file", "-f", help="Read prompt from file (otherwise stdin)")
    ap.add_argument("--print-improved", dest="print_improved", action="store_true",
                    help="Print improved prompt only")
    ap.add_argument("--show-diff", dest="show_diff", action="store_true",
                    help="Show unified diff between original and improved")
    ap.add_argument("--write", "-w", help="Path to write improved prompt")
    args = ap.parse_args()

    raw = pathlib.Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    res = score_and_improve(raw)

    if args.print_improved:
        print(res["improved"])
        return

    if args.show_diff:
        print(res["diff"])
        return

    if args.write:
        out_path = pathlib.Path(args.write)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(res["improved"], encoding="utf-8")

    print(json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
