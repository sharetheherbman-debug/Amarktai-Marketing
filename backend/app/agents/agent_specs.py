from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class BaseAgent:
    name: str
    purpose: str
    inputs: list[str]
    outputs: list[str]
    capability_requirements: list[str]
    provider_dependencies: list[str]
    fallback_behavior: str
    status: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class StrategyAgent(BaseAgent):
    def __init__(self): super().__init__("StrategyAgent", "Build campaign strategy from business context.", ["business profile", "objective"], ["campaign strategy"], ["campaign_strategy"], ["genx", "qwen"], "Template strategy fallback", "available")


class ScraperAgent(BaseAgent):
    def __init__(self): super().__init__("ScraperAgent", "Scrape and structure website intelligence.", ["url"], ["structured intelligence"], ["website_scrape"], ["firecrawl"], "HTTP scrape fallback", "available")


class CopyAgent(BaseAgent):
    def __init__(self): super().__init__("CopyAgent", "Generate platform copy.", ["strategy", "platform"], ["post copy"], ["platform_copy"], ["genx", "qwen"], "Template copy fallback", "available")


class CreativeDirectorAgent(BaseAgent):
    def __init__(self): super().__init__("CreativeDirectorAgent", "Select creative direction and format.", ["platform", "objective"], ["format plan"], ["campaign_strategy"], ["template"], "Use default platform strategy", "available")


class ImagePromptAgent(BaseAgent):
    def __init__(self): super().__init__("ImagePromptAgent", "Generate image prompts.", ["brief"], ["image prompt"], ["image_prompt"], ["genx", "qwen"], "Template image prompt", "available")


class VideoScriptAgent(BaseAgent):
    def __init__(self): super().__init__("VideoScriptAgent", "Generate video scripts and shot lists.", ["brief"], ["video script"], ["video_script"], ["genx", "qwen"], "Template video brief fallback", "available")


class AvatarScriptAgent(BaseAgent):
    def __init__(self): super().__init__("AvatarScriptAgent", "Generate talking avatar scripts.", ["brief"], ["avatar script"], ["talking_avatar_script"], ["genx", "qwen"], "Template avatar script fallback", "available")


class ComplianceAgent(BaseAgent):
    def __init__(self): super().__init__("ComplianceAgent", "Review compliance and policy fit.", ["content"], ["risk findings"], ["compliance_review"], ["template"], "Conservative static checks", "available")


class PlatformIntelligenceAgent(BaseAgent):
    def __init__(self): super().__init__("PlatformIntelligenceAgent", "Apply platform rules and algorithm-fit guidance.", ["platform", "content"], ["fit score and suggestions"], ["algorithm_fit_review"], ["template"], "Fallback to baseline social rules", "available")


class SchedulerAgent(BaseAgent):
    def __init__(self): super().__init__("SchedulerAgent", "Create scheduling drafts.", ["drafts"], ["schedule plan"], ["schedule_planning"], ["template"], "Manual schedule suggestions", "available")


class LearningAgent(BaseAgent):
    def __init__(self): super().__init__("LearningAgent", "Generate daily learning insights.", ["analytics", "content history"], ["learning insights"], ["performance_learning"], ["template"], "Manual-run insights only", "degraded")


def all_agents() -> list[BaseAgent]:
    return [
        StrategyAgent(),
        ScraperAgent(),
        CopyAgent(),
        CreativeDirectorAgent(),
        ImagePromptAgent(),
        VideoScriptAgent(),
        AvatarScriptAgent(),
        ComplianceAgent(),
        PlatformIntelligenceAgent(),
        SchedulerAgent(),
        LearningAgent(),
    ]
