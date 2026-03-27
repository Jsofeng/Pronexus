import httpx
from backend.prompts import B2B_STYLE_GUIDE, POST_TEMPLATE
import google.generativeai as genai
from datetime import datetime, timedelta

class DataPipeline:
    
    @staticmethod
    async def fetch_hn_signals():
        url = "https://hn.algolia.com/api/v1/search?tags=story&numericFilters=points>100"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            return [{"text": h["title"], "source": "HN"} for h in r.json()["hits"][:15]]

    @staticmethod
    async def fetch_reddit_signals():
        url = "https://www.reddit.com/r/programming/hot.json?limit=10"
        headers = {"User-Agent": "SignalPost/1.0"}
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers)
            posts = r.json()["data"]["children"]
            return [{"text": p["data"]["title"], "source": "r/programming"} for p in posts]
        


class LinkedInGenerator:
    def __init__(self, api_key: str):
    
        genai.configure(api_key=api_key)
        
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        print("🚀 Generator Initialized with API Key")
    
    async def generate_post(self, industry: str, topic: str):

        signals = await DataPipeline.fetch_hn_signals()
        trend_brief = "\n".join([f"- {s['text']}" for s in signals[:3]])
        
        prompt = POST_TEMPLATE.format(
            industry=industry,
            topic_brief=trend_brief,
            style_guide=B2B_STYLE_GUIDE
        )
        
        
        response = self.model.generate_content(
            prompt, 
            request_options={"timeout": 600} 
        )        
        
        return response.text
    
    async def generate_reddit_post(self, industry: str, topic: str):

        signals = await DataPipeline.fetch_reddit_signals()
        trend_brief = "\n".join([f"- {s['text']}" for s in signals[:3]])

        prompt = POST_TEMPLATE.format(
            industry=industry,
            topic_brief=trend_brief,
            style_guide=B2B_STYLE_GUIDE
        )

        response = self.model.generate_content(
            prompt, 
            request_options={"timeout": 600} 
        )        
        
        return response.text
    