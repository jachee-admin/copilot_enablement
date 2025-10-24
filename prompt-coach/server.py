from fastapi import FastAPI
from pydantic import BaseModel
from coach.scorer import score_and_improve

app = FastAPI(title="Prompt Coach API")

class PromptIn(BaseModel):
    text: str

@app.post("/score")
def score(p: PromptIn):
    return score_and_improve(p.text)

# uvicorn server:app --reload --port 8088
# # POST http://localhost:8088/score {"text":"Write a script..."}