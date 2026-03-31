import json, re
import asyncio
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.routes.services.pipeline import DataPipeline, build_gen_prompts
from backend.routes.services.linter import score_post

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenRequest(BaseModel):
    api_key: str
    niche: str

def extract_json(text: str):
    match = re.search(r'\[.*\]|\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


@app.post("/api/generate")
async def generate(req: GenRequest):
    try:
        if not req.api_key:
            raise ValueError("API Key is missing")

        genai.configure(api_key=req.api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        print("Step 1: Fetching HN signals...")
        try:
            signals = await asyncio.wait_for(DataPipeline.fetch_hn_signals(), timeout=10.0)
        except asyncio.TimeoutError:
            raise ValueError("Timed out fetching Hacker News signals (>10s). Check your network.")

        if not signals:
            raise ValueError("No signals returned from Hacker News.")
        print(f"Step 1 OK: Got {len(signals)} signals.")

        prompt = build_gen_prompts(req.niche, signals)
        print(f"Step 2 OK: Prompt built for '{req.niche}'.")

        print("Step 3: Calling Gemini API...")
        try:
            response = await asyncio.wait_for(
                model.generate_content_async(prompt),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            raise ValueError(
                "Gemini API timed out after 30 seconds. "
                "Try: (1) Check your API key is valid, "
                "(2) Reduce prompt size, "
                "(3) Try again in a moment."
            )
        print("Step 3 OK: Gemini responded.")

        if not response.candidates:
            feedback = getattr(response, 'prompt_feedback', 'No feedback available')
            raise ValueError(f"Gemini blocked the response. Feedback: {feedback}")

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            finish_reason = getattr(candidate, 'finish_reason', 'unknown')
            raise ValueError(f"Gemini returned empty content. Finish reason: {finish_reason}")

        response_text = response.text
        print(f"Step 4 OK: Response text length = {len(response_text)} chars.")
        print(f"Preview: {response_text[:300]}")

        try:
            posts = extract_json(response_text)
        except Exception as json_err:
            print(f"JSON Parse Failure. Full response:\n{response_text}")
            raise ValueError(f"Gemini returned invalid JSON: {str(json_err)}")

        if isinstance(posts, list) and len(posts) > 0 and isinstance(posts[0], list):
            posts = posts[0]
        if not isinstance(posts, list):
            posts = [posts]

        final_posts = []
        for p in posts:
            if not isinstance(p, dict) or "hook" not in p or "body" not in p:
                continue
            lint = score_post(p)
            p.update({"lint_score": lint.get("score", 0), "flags": lint.get("flags", [])})
            final_posts.append(p)

        if not final_posts:
            raise ValueError("Posts generated but none passed validation. Raw output logged above.")

        print(f"Done: Returning {len(final_posts)} post(s).")
        return {"posts": final_posts}

    except HTTPException:
        raise
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"message": "SignalPost API is LIVE!"}