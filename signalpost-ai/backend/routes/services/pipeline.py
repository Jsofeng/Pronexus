import httpx
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
        # Using .json to avoid complex OAuth for a quick demo
        url = "https://www.reddit.com/r/programming/hot.json?limit=10"
        headers = {"User-Agent": "SignalPost/1.0"}
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers)
            posts = r.json()["data"]["children"]
            return [{"text": p["data"]["title"], "source": "r/programming"} for p in posts]