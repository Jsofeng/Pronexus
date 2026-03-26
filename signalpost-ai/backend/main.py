import os, json
import google.genai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from routes.services.pipeline import DataPipeline
from routes.services.linter import score_post
from routes.services.prompts import build_gen_prompt

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # This allows any frontend to call your API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class GenRequest(BaseModel):
    api_key: str
    niche: str

@app.post("/api/generate")
async def generate(req: GenRequest):
    genai.configure(api_key=req.api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    signals = await DataPipeline.fetch_hn_signals()
    prompt = build_gen_prompt(req.niche, signals)
    
    response = model.generate_content(prompt)
    posts = json.loads(response.text.replace("```json", "").replace("```", ""))
    
    for p in posts:
        lint = score_post(p)
        p.update({"score": lint["score"], "flags": lint["flags"]})
        
    return {"posts": posts}