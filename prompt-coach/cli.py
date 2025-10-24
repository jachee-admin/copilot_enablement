#!/usr/bin/env python
import sys, json, argparse
from coach.scorer import score_and_improve

def main():
    ap = argparse.ArgumentParser(description="Prompt Coach (AI Prompt Optimizer)")
    ap.add_argument("--file", "-f", help="Read prompt from file")
    ap.add_argument("--print-improved", action="store_true", help="Print improved prompt only")
    args = ap.parse_args()

    raw = open(args.file, "r", encoding="utf-8").read() if args.file else sys.stdin.read()
    res = score_and_improve(raw)

    if args.print_improved:
        print(res["improved"])
        sys.exit(0)

    print(json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()

# export OPENAI_API_KEY=sk-...
# python -m prompt_coach.cli -f my_prompt.txt