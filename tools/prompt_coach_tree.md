```
prompt-coach/
├── README.md
├── pyproject.toml
├── coach
│   ├── __init__.py
│   ├── heuristics.py          # fast local checks (no API)
│   ├── scorer.py              # aggregates heuristics + model judgement
│   ├── openai_client.py       # thin wrapper for OpenAI chat
│   ├── templates.py           # system prompts using your common library
│   └── utils.py
├── cli.py                     # `python -m prompt_coach ...`
├── server.py                  # FastAPI service
├── tests
│   ├── test_heuristics.py
│   └── test_scorer.py
└── .env.example               # OPENAI_API_KEY=...
```