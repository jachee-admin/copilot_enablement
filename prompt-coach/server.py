from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from coach.scorer import score_and_improve

app = FastAPI(title="Prompt Coach API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class PromptIn(BaseModel):
    text: str

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/score")
def score(p: PromptIn):
    return score_and_improve(p.text)


# uvicorn server:app --reload --port 8088
# curl -s localhost:8088/health
# curl -s localhost:8088/score -H 'content-type: application/json' -d '{"text":"write a postgres playbook"}' | jq