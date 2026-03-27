import asyncio
import os
from dotenv import load_dotenv
from backend.routes.services.pipeline import LinkedInGenerator

load_dotenv()

async def main():
    gen = LinkedInGenerator(api_key=os.getenv("GOOGLE_API_KEY"))
    post = await gen.generate_post("Investment Banking", "AI workflows in Excel")
    print("\n--- GENERATED POST ---")
    print(post)

if __name__ == "__main__":
    asyncio.run(main())