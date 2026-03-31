B2B_STYLE_GUIDE = """
- RHYTHM: Use 1-2-3 punch (Short line, medium line, list).
- HOOKS: Use "Pattern Interrupts." (e.g., "Most engineers think X. They are wrong.")
- NO SLOP: Delete words like 'Unleash', 'Tapestry', 'Revolutionizing'.
- CTAs: Soft value-adds only. No "Buy now."
"""


POST_TEMPLATE = """You are a B2B content strategist for {industry}.

Using these trending topics:
{topic_brief}

Write exactly 1 LinkedIn post. Rules:
1. Hook must be under 10 words.
2. Include one specific number or metric.
3. Final line must be a contrarian take.
4. Use white space between paragraphs.

{style_guide}

Respond ONLY with a valid JSON array, no markdown, no explanation:
[{{"hook": "your hook here", "body": "your body here"}}]"""