import re 

BANNED_PHRASES = ["game-changer", "delve", "rapidly evolving", "unleash", "transformative"]

def score_post(post: dict) -> dict:
    score = 100
    flags = []
    content = (post.get("hook", "") + " " + post.get("body", " ")).lower()

    if any(p in content for p in BANNED_PHRASES):
        score -= 25
        flags.append("generic_ai_phrasing")

    if "-" in content:
        score -= 10
        flags.append("em_dash_detected")

    if not re.search(r'\d+%|\d+x|\$\d+', content):
        score -= 15
        flags.append("missing_hard_metrics")

    return {"score": max(0, score), "flags": flags}