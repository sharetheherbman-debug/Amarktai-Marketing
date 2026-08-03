"""
AMarkTAI Autonomous Marketing Agent Swarm v2
Content Multiplication: 1 URL → 20-30 posts across 6+ platforms
All LLM calls routed through OGA unified endpoint
API keys managed via dashboard setup screen (not .env)
"""
import os, json, requests
from typing import TypedDict
from langgraph.graph import StateGraph, END
from openai import OpenAI

oga = OpenAI(
    base_url=os.getenv("OGA_API_URL", "http://localhost:8080/v1"),
    api_key="not-needed"
)
SCRAPER = os.getenv("SCRAPER_API_URL", "http://localhost:8081")


class MarketingState(TypedDict):
    url: str
    scraped_content: str
    blog_post: str
    video_script: str
    video_prompts: list
    short_clips: list
    tweets: list
    linkedin_posts: list
    email_newsletter: str
    music_prompt: str
    carousel_captions: list
    output_ready: bool
    errors: list


def llm(model: str, system: str, user: str, max_tokens=2000, temp=0.7) -> str:
    """Unified LLM call through OGA with automatic tier routing"""
    try:
        r = oga.chat.completions.create(
            model=model, messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ], max_tokens=max_tokens, temperature=temp
        )
        return r.choices[0].message.content or ""
    except Exception as e:
        return f"[ERROR: {str(e)}]"


def scrape_node(state: MarketingState) -> dict:
    """Scrape target URL via self-hosted Crawlee"""
    try:
        resp = requests.post(f"{SCRAPER}/scrape", json={"url": state["url"]}, timeout=60)
        resp.raise_for_status()
        return {"scraped_content": resp.json().get("content", "")[:30000]}
    except Exception as e:
        return {"scraped_content": "", "errors": [f"Scrape: {e}"]}


def blog_node(state: MarketingState) -> dict:
    """Generate SEO-optimized blog post (Tier 2)"""
    c = state.get("scraped_content", "")
    if not c:
        return {"blog_post": ""}
    post = llm("amark-standard-llm",
        "Write a 1500-word SEO blog post with H2 headings, meta description, and 5 keywords.",
        f"Source content:\n\n{c[:15000]}", max_tokens=3000)
    return {"blog_post": post}


def video_script_node(state: MarketingState) -> dict:
    """Generate video script from blog post (Tier 2)"""
    blog = state.get("blog_post", "")
    if not blog:
        return {"video_script": ""}
    script = llm("amark-standard-llm",
        "Create a 3-minute marketing video script with scene descriptions and narration.",
        f"Blog post:\n\n{blog[:8000]}", max_tokens=2000)
    return {"video_script": script}


def video_prompts_node(state: MarketingState) -> dict:
    """Generate per-scene AI video prompts (Tier 2)"""
    script = state.get("video_script", "")
    if not script:
        return {"video_prompts": []}
    raw = llm("amark-standard-llm",
        "Extract 5 scene descriptions as JSON array of visual prompts for AI video generation.",
        f"Script:\n\n{script[:5000]}", max_tokens=1500, temp=0.5)
    try:
        prompts = json.loads(raw) if "[" in raw else [raw]
    except json.JSONDecodeError:
        prompts = [raw]
    return {"video_prompts": prompts}


def short_clips_node(state: MarketingState) -> dict:
    """Repurpose video script into 5 short-form clip scripts (Tier 3 - free)"""
    script = state.get("video_script", "")
    if not script:
        return {"short_clips": []}
    raw = llm("amark-free-llm",
        "Create 5 standalone 30-second TikTok/Reels scripts from this video script. JSON array.",
        f"Full script:\n\n{script[:5000]}", max_tokens=2000, temp=0.8)
    try:
        clips = json.loads(raw) if "[" in raw else [raw]
    except json.JSONDecodeError:
        clips = [raw]
    return {"short_clips": clips}


def tweets_node(state: MarketingState) -> dict:
    """Generate 10 tweet threads from blog post (Tier 3 - free)"""
    blog = state.get("blog_post", "")
    if not blog:
        return {"tweets": []}
    raw = llm("amark-free-llm",
        "Create 10 engaging tweet threads (3-5 tweets each) from this blog. JSON array of arrays.",
        f"Blog:\n\n{blog[:8000]}", max_tokens=3000, temp=0.9)
    try:
        tweets = json.loads(raw) if "[" in raw else [raw]
    except json.JSONDecodeError:
        tweets = [raw]
    return {"tweets": tweets}


def linkedin_node(state: MarketingState) -> dict:
    """Generate 3 LinkedIn posts with different angles (Tier 3 - free)"""
    blog = state.get("blog_post", "")
    if not blog:
        return {"linkedin_posts": []}
    raw = llm("amark-free-llm",
        "Create 3 LinkedIn posts from different angles: 1) thought leadership, 2) practical tips, 3) story-driven. JSON array.",
        f"Blog:\n\n{blog[:8000]}", max_tokens=2000, temp=0.7)
    try:
        posts = json.loads(raw) if "[" in raw else [raw]
    except json.JSONDecodeError:
        posts = [raw]
    return {"linkedin_posts": posts}


def email_node(state: MarketingState) -> dict:
    """Generate email newsletter from blog (Tier 2)"""
    blog = state.get("blog_post", "")
    if not blog:
        return {"email_newsletter": ""}
    newsletter = llm("amark-standard-llm",
        "Write a compelling email newsletter with subject line, preview text, and CTA.",
        f"Blog post:\n\n{blog[:8000]}", max_tokens=1500)
    return {"email_newsletter": newsletter}


def music_node(state: MarketingState) -> dict:
    """Generate music style prompt (Tier 3 - free)"""
    content = state.get("scraped_content", "")[:2000]
    prompt = llm("amark-free-llm",
        "Suggest background music style for marketing video. Format: 'genre, mood, instruments'",
        f"Content: {content}", max_tokens=100, temp=0.8)
    return {"music_prompt": prompt or "upbeat corporate, positive, piano synth"}


def carousel_node(state: MarketingState) -> dict:
    """Generate 5 Instagram carousel slide captions (Tier 3 - free)"""
    blog = state.get("blog_post", "")
    if not blog:
        return {"carousel_captions": []}
    raw = llm("amark-free-llm",
        "Create 5 Instagram carousel slide captions with hook on slide 1 and CTA on slide 5. JSON array.",
        f"Blog:\n\n{blog[:5000]}", max_tokens=1500, temp=0.8)
    try:
        captions = json.loads(raw) if "[" in raw else [raw]
    except json.JSONDecodeError:
        captions = [raw]
    return {"carousel_captions": captions}


def finalize_node(state: MarketingState) -> dict:
    """Validate all outputs generated"""
    has_content = bool(state.get("blog_post") and state.get("video_script"))
    has_errors = bool(state.get("errors"))
    return {"output_ready": has_content and not has_errors}


def route_after_scrape(state: MarketingState) -> str:
    if state.get("errors") and not state.get("scraped_content"):
        return "end"
    return "blog"


# Build graph with parallel branches where possible
g = StateGraph(MarketingState)
g.add_node("scrape", scrape_node)
g.add_node("blog", blog_node)
g.add_node("video_script", video_script_node)
g.add_node("video_prompts", video_prompts_node)
g.add_node("short_clips", short_clips_node)
g.add_node("tweets", tweets_node)
g.add_node("linkedin", linkedin_node)
g.add_node("email", email_node)
g.add_node("music", music_node)
g.add_node("carousel", carousel_node)
g.add_node("finalize", finalize_node)

g.set_entry_point("scrape")
g.add_conditional_edges("scrape", route_after_scrape, {"blog": "blog", "end": END})
g.add_edge("blog", "video_script")
g.add_edge("video_script", "video_prompts")
# Parallel fan-out from blog for text derivatives
g.add_edge("blog", "tweets")
g.add_edge("blog", "linkedin")
g.add_edge("blog", "email")
g.add_edge("blog", "carousel")
g.add_edge("scrape", "music")
# Converge all branches to finalize
for node in ["video_prompts", "short_clips", "tweets", "linkedin", "email", "music", "carousel"]:
    g.add_edge(node, "finalize")
g.add_edge("video_prompts", "short_clips")
g.add_edge("finalize", END)

app = g.compile()
