"""
AMarkTAI Autonomous Marketing Agent Swarm
LangGraph workflow: Scrape → Author → Video → Music → Output
"""
import os
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from openai import OpenAI

# All agents use OGA unified endpoint
oga_client = OpenAI(
    base_url=os.getenv("OGA_API_URL", "http://localhost:8080/v1"),
    api_key="not-needed"  # OGA handles auth internally
)

SCRAPER_URL = os.getenv("SCRAPER_API_URL", "http://localhost:8081")


class MarketingState(TypedDict):
    url: str
    scraped_content: str
    script: str
    video_prompt: str
    music_prompt: str
    output_ready: bool
    errors: list


def scrape_node(state: MarketingState) -> dict:
    """Scrape target URL via self-hosted Crawlee API"""
    import requests
    try:
        resp = requests.post(f"{SCRAPER_URL}/scrape", json={"url": state["url"]}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return {"scraped_content": data.get("content", "")[:30000]}
    except Exception as e:
        return {"scraped_content": "", "errors": [f"Scrape failed: {str(e)}"]}


def author_node(state: MarketingState) -> dict:
    """Generate video script from scraped content using Tier 2 (DeepInfra)"""
    if not state.get("scraped_content"):
        return {"script": "", "errors": ["No content to author from"]}

    response = oga_client.chat.completions.create(
        model="amark-standard-llm",
        messages=[
            {"role": "system", "content": "You are a professional marketing copywriter. Create a concise video script (max 500 words) with scene descriptions."},
            {"role": "user", "content": f"Create a marketing video script from this content:\n\n{state['scraped_content'][:15000]}"}
        ],
        max_tokens=2000,
        temperature=0.7
    )
    script = response.choices[0].message.content or ""
    return {"script": script, "video_prompt": script[:1000]}


def video_prompt_node(state: MarketingState) -> dict:
    """Refine video generation prompt using Tier 2"""
    if not state.get("script"):
        return {"video_prompt": ""}

    response = oga_client.chat.completions.create(
        model="amark-standard-llm",
        messages=[
            {"role": "system", "content": "Convert this script into optimized prompts for AI video generation. One prompt per scene, max 5 scenes."},
            {"role": "user", "content": state["script"][:5000]}
        ],
        max_tokens=1500,
        temperature=0.5
    )
    return {"video_prompt": response.choices[0].message.content or ""}


def music_prompt_node(state: MarketingState) -> dict:
    """Generate music style prompt based on content mood"""
    response = oga_client.chat.completions.create(
        model="amark-free-llm",  # Free tier sufficient for simple prompt
        messages=[
            {"role": "system", "content": "Suggest a music style and mood for a marketing video. Reply in format: 'genre, mood, instruments'"},
            {"role": "user", "content": f"Content summary: {state.get('scraped_content', '')[:2000]}"}
        ],
        max_tokens=100,
        temperature=0.8
    )
    return {"music_prompt": response.choices[0].message.content or "upbeat corporate, positive, piano and synth"}


def finalize_node(state: MarketingState) -> dict:
    """Mark workflow complete"""
    has_errors = bool(state.get("errors"))
    has_output = bool(state.get("script") and state.get("video_prompt"))
    return {"output_ready": has_output and not has_errors}


def should_continue(state: MarketingState) -> str:
    """Route based on whether scraping succeeded"""
    if state.get("errors") and not state.get("scraped_content"):
        return "end"
    return "author"


# Build the graph
workflow = StateGraph(MarketingState)
workflow.add_node("scrape", scrape_node)
workflow.add_node("author", author_node)
workflow.add_node("video_prompt", video_prompt_node)
workflow.add_node("music_prompt", music_prompt_node)
workflow.add_node("finalize", finalize_node)

workflow.set_entry_point("scrape")
workflow.add_conditional_edges("scrape", should_continue, {"author": "author", "end": END})
workflow.add_edge("author", "video_prompt")
workflow.add_edge("video_prompt", "music_prompt")
workflow.add_edge("music_prompt", "finalize")
workflow.add_edge("finalize", END)

app = workflow.compile()
