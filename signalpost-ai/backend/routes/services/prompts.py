def build_gen_prompt(niche, trends):
    trend_context = "\n".join([f"- {t['text']}" for t in trends])
    return f"""
    You are a Senior Software Engineer writing for LinkedIn. 
    NICHE: {niche}
    TRENDS: {trend_context}

    STYLE RULES:
    1. Hook: Start with a specific number, a hard truth, or a 2-sentence scene. 
    2. Format: Short lines. Blank line between every paragraph.
    3. No Em Dashes: Use colons or periods instead.
    4. Metrics: Use specific numbers like 73%, 11 minutes, or 4.2x.

    OUTPUT: RAW JSON array of 3 objects with "hook" and "body" keys.
    """