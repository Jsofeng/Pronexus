# SignalPost  Workflow Design & System Overview

---

## 1. Data Sources & Ingestion

### Current Sources

| Source | Endpoint | Cadence | Signal Type |
|---|---|---|---|
| Hacker News | `hn.algolia.com/api/v1/search` | Per request (on-demand) | Tech discourse, trending stories |
| Reddit r/programming | `reddit.com/r/programming/hot.json` | Per request (on-demand) | Developer pain points, hot topics |

### How Ingestion Works

Both sources are fetched via `httpx` async HTTP calls at the moment a user clicks **Generate Posts**. The pipeline pulls the top 15–25 items from each source, shuffles them to avoid always surfacing the same headlines, and selects a random subset of 3 to inject into the prompt as `topic_brief`.

The shuffle is intentional  it ensures variety across multiple generations in the same session, simulating a broader "scan" of the internet rather than always anchoring to the #1 trending post.

### What a Production Cadence Would Look Like

In the current architecture, ingestion is **synchronous and on-demand**  signals are fetched fresh every time a user generates posts. This works for a prototype but doesn't scale.

A production cadence would decouple ingestion from generation:

```
Scheduler (cron / Celery beat)
  └── Every 6 hours: fetch HN + Reddit + RSS feeds
        └── Deduplicate, score by engagement
              └── Write to signals cache (Redis / Postgres)
                    └── FastAPI route reads from cache (fast)
```

This means the API call becomes near-instant (no live HTTP fetches in the hot path), and you can expand sources without adding latency.

---

## 2. Prompt Engineering Strategy

### Template Structure

The prompt is assembled in `prompts.py` using a `POST_TEMPLATE` string with three injected variables:

- `{industry}`  the user-selected niche (e.g. "Data Engineering")
- `{topic_brief}`  3 bullet points from the live signal fetch
- `{style_guide}`  a static set of writing constraints

```
Role definition
  └── Topic context (live signals)
        └── Hard constraints (hook length, metric requirement, contrarian take)
              └── Style guide (banned phrases, CTA rules, rhythm)
                    └── Output format instruction (strict JSON)
```

### Key Prompt Engineering Decisions

**1. Constraints over instructions**

Rather than asking the model to "write a good LinkedIn post," the template gives it specific, measurable rules: hook under 10 words, one hard number, final line must be a contrarian take. This reduces variance and makes output quality consistent enough to lint programmatically.

**2. Output format locked to JSON**

The prompt explicitly says: *"Respond ONLY with a valid JSON array, no markdown, no explanation."* This is critical for a pipeline that must parse and score the output. Without this, models frequently wrap JSON in markdown fences or add preamble text, breaking the parser.

**3. Style guide as a negative constraint list**

`B2B_STYLE_GUIDE` is mostly a list of things *not* to do ("delete words like 'Unleash', 'Tapestry'") rather than aspirational guidance. Negative constraints are more reliable than positive ones the model has a clear rejection criterion rather than an ambiguous goal.

**4. One post per call**

The template asks for exactly one post. Asking for multiple posts in a single call increases response length, which increases latency and the probability of malformed JSON. One post per call is faster, more reliable, and easier to validate.

### Evaluation (Linting)

Output is passed through `linter.py` which applies a rule-based scoring function:

| Check | Penalty | Flag |
|---|---|---|
| Banned AI phrases detected | -25 pts | `generic_ai_phrasing` |
| Em-dash detected | -10 pts | `em_dash_detected` |
| No hard metric (`\d+%`, `\d+x`, `$\d+`) | -15 pts | `missing_hard_metrics` |

A `lint_score` out of 100 is returned to the frontend alongside any flags. Posts are not rejected by score they are surfaced to the user with transparency, which is the right call for a v1 where false positives from the linter would be frustrating.

---

## 3. Design Choices & Tradeoffs

| Decision | Why | Tradeoff |
|---|---|---|
| On-demand signal fetch | No infrastructure needed, always fresh | Adds ~1–2s latency per request; fails if HN/Reddit is down |
| Gemini 1.5 Flash | Fast, cheap, good at structured output | Less nuanced than GPT-4o or Claude Opus for long-form prose |
| Rule-based linter | Deterministic, zero cost, fast | Misses semantic quality issues (boring posts that pass all rules) |
| Single post per prompt call | Reduces latency and JSON parse failures | Requires multiple calls if user wants volume |
| Shuffle + random signal sampling | Adds variety without extra API calls | Reduces reproducibility; same niche can produce very different results |

---

## 4. If I Had More Time

### What I Would Expand

**More signal sources.** HN and r/programming skew heavily toward a software engineering audience. Adding RSS feeds from industry-specific Substack newsletters, LinkedIn trending topics (via unofficial scraping), and G2/Gartner review trends would produce signals far more relevant to niches like Cybersecurity or Data Engineering.

**Audience persona layer.** Right now the only input is "niche." A persona system (CTO at Series B SaaS vs. indie developer vs. VP of Engineering at enterprise) would dramatically improve post relevance. A single extra dropdown or a freetext "who are you writing for?" field could route to a persona-specific system prompt.

**Post history and deduplication.** There's nothing stopping the same post from being generated twice. A simple Postgres table storing past hooks and a semantic similarity check (via embeddings) before generation would prevent repetition.

**Multi-platform output.** The body format for LinkedIn is different from Twitter/X threads, Bluesky posts, or newsletter openers. The same signal + persona could fan out to multiple formats from one generation call.

### How I Would Make It More Intelligent

**Feedback loop.** Let users rate posts with a thumbs up/down. Store ratings against the signals and prompt variant used. Fine-tune a classifier over time to predict which signal + niche combinations produce high-rated output. Use this to pre-filter signals before they hit the LLM.

**Semantic signal scoring.** Not all HN stories are equally relevant to a given niche. Before building the `topic_brief`, run a lightweight embedding similarity check between each signal title and the target niche. Only inject the top-3 by cosine similarity rather than random selection.

**LLM-as-judge for quality.** Replace the rule-based linter with a second, cheaper LLM call that scores the generated post on: specificity, credibility, non-obviousness, and engagement potential. This catches semantic failures the regex linter can't (e.g. a post that has a number but is still a generic platitude).

### How I Would Make It More Cost-Effective

**Prompt caching.** The `B2B_STYLE_GUIDE` and structural instructions are static. Anthropic and Google both support prompt caching marking the static prefix as cacheable reduces token costs by 80–90% on the system prompt portion.

**Tiered model routing.** Use a cheap, fast model (Gemini Flash, GPT-4o mini) for initial generation, then only escalate to a premium model if the lint score is below a threshold. Most posts won't need the upgrade.

**Signal cache.** As described above fetch signals on a 6-hour cron rather than per-request. This eliminates the live HTTP cost and latency from every user request.

### How I Would Make It Safer

**Hallucination guard on metrics.** The prompt requires a "hard number" but the model will invent one if the signals don't contain real data. A post-processing step should flag any number that doesn't appear in the source signals as `unverified_metric`, making it visible to the user before they publish.

**Brand safety filter.** A secondary pass checking for unintentional mentions of competitors, sensitive topics, or claims that could be read as financial advice. Especially important for the Investment Banking niche already in `test_gen.py`.

**Rate limiting per API key.** Currently any valid Gemini key can hammer the endpoint indefinitely. Adding per-key rate limiting (Redis + sliding window counter) prevents abuse and runaway costs if a key leaks.

### How I Would Scale to Hundreds of Posts per Week While Keeping Quality High

The core scaling challenge is that quality degrades with volume if every post is generated the same way. The strategy is to **scale the pipeline, not just the throughput.**

**Stage 1  Async job queue (dozens → low hundreds/week)**

Move generation off the synchronous request/response cycle into a background worker queue (Celery + Redis). The user submits a job, gets a job ID, and polls for results. This decouples generation time from HTTP timeout constraints and allows retries on failure.

```
POST /api/generate → { job_id: "abc123" }
GET  /api/jobs/abc123 → { status: "complete", posts: [...] }
```

**Stage 2  Batch generation with diversity enforcement (hundreds/week)**

When generating many posts for the same niche in a week, enforce semantic diversity across the batch. Before each generation, embed all posts already generated that week and reject any new post whose embedding is within a similarity threshold of an existing one. Re-generate until the batch is diverse.

**Stage 3  Human-in-the-loop quality gate**

At volume, an LLM-as-judge score above a threshold (e.g. 75/100) auto-approves the post. Posts scoring below threshold enter a human review queue rather than being discarded, since the issue might be the signal rather than the generation. A simple internal review UI (even just a Retool dashboard) makes this manageable with minimal effort.

**Stage 4  Per-niche fine-tuning signals**

At hundreds of posts per week, you accumulate enough approved/rejected examples per niche to fine-tune a small model (or build a high-quality few-shot library) specifically for that niche. This compounds the more posts generated for "Cybersecurity," the better the Cybersecurity prompt becomes, without increasing cost.
