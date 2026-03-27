import os, json
import google.generativeai as genai 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.routes.services.pipeline import DataPipeline
from backend.routes.services.linter import score_post
from backend.routes.services.pipeline import LinkedlnGenerator

app = FastAPI()

generator = LinkedlnGenerator(api_key=os.getenv("GOOGLE_API_KEY"))

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

@app.get("/")
async def root():
    return {"message": "Pronexus API is LIVE!"}


@app.post("/generate")
async def generate_posts():

    industry = "Computer Science / AI Engineering"
    topic = "Agentic Workflows vs Static Pipelines"
    
    post = await generator.generate_post(industry, topic)
    return {"industry": industry, "post": post}