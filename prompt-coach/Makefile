.PHONY: setup test run api format

setup:
\tpython -m pip install -e .\n\tpip install pytest pre-commit

test:
\tpytest -q

run:
\tpython -m prompt_coach.cli -f sample_prompt.txt --show-diff

api:
\tuvicorn server:app --port 8088 --reload

format:
\tpre-commit run --all-files || true
