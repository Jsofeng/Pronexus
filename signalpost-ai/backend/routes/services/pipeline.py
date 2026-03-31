import httpx
import json
import random
import google.generativeai as genai
from backend.prompts import B2B_STYLE_GUIDE, POST_TEMPLATE


class DataPipeline:
    @staticmethod
    async def fetch_hn_signals():
        url = "https://hn.algolia.com/api/v1/search?tags=story&numericFilters=points>100"
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            hits = r.json().get("hits", [])
            random.shuffle(hits)
            return [{"text": h["title"], "source": "HN"} for h in hits[:15]]

    @staticmethod
    async def fetch_reddit_signals():
        url = "https://www.reddit.com/r/programming/hot.json?limit=25"
        headers = {"User-Agent": "SignalPost/1.0"}
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            data = r.json()
            if "data" in data and "children" in data["data"]:
                posts = data["data"]["children"]
                random.shuffle(posts)
                return [{"text": p["data"]["title"], "source": "r/programming"} for p in posts]
            return []


class LinkedInGenerator:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        print("🚀 Generator Initialized")

    def _clean_json_response(self, text: str):
        try:
            cleaned = text.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            while isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                data = data[0]
            return data if isinstance(data, list) else []
        except Exception as e:
            print(f"JSON Parsing Error: {e}")
            return []

    async def generate_post(self, industry: str, topic: str):
        signals = await DataPipeline.fetch_hn_signals()
        selected = random.sample(signals, min(len(signals), 3))
        trend_brief = "\n".join([f"- {s['text']}" for s in selected])
        prompt = POST_TEMPLATE.format(
            industry=industry, topic_brief=trend_brief, style_guide=B2B_STYLE_GUIDE
        )
        response = await self.model.generate_content_async(prompt)
        return self._clean_json_response(response.text)

    async def generate_reddit_post(self, industry: str, topic: str):
        signals = await DataPipeline.fetch_reddit_signals()
        selected = random.sample(signals, min(len(signals), 3))
        trend_brief = "\n".join([f"- {s['text']}" for s in selected])
        prompt = POST_TEMPLATE.format(
            industry=industry, topic_brief=trend_brief, style_guide=B2B_STYLE_GUIDE
        )
        response = await self.model.generate_content_async(prompt)
        return self._clean_json_response(response.text)


def build_gen_prompts(niche: str, signals: list) -> str:
    """Stand-alone helper used by the FastAPI route.
    Keeps only 3 signals to minimize prompt size and reduce Gemini latency.
    """
    random.shuffle(signals)
    trend_brief = "\n".join([f"- {s['text']}" for s in signals[:3]])
    return POST_TEMPLATE.format(
        industry=niche,
        topic_brief=trend_brief,
        style_guide=B2B_STYLE_GUIDE
    )