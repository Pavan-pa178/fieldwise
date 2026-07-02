from __future__ import annotations
import json
from .base_agent import BaseAgent, AgentResult
from .llm_client import LLMClient


class VisionAgent(BaseAgent):
    name = "vision_agent"

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient()

    def run(self, *, image_path: str) -> AgentResult:
        prompt = (
            "Examine this crop photo. Describe visible symptoms (leaf spots, "
            "discoloration, wilting, insects, etc.) and classify the likely "
            "category as disease, pest, or nutrient_deficiency."
        )
        response = self.llm.analyze_image(image_path, prompt)

        try:
            parsed = json.loads(response.text)
        except (json.JSONDecodeError, AttributeError):
            parsed = {"visible_symptoms": response.text, "likely_category": "unknown"}

        return AgentResult(
            agent_name=self.name,
            success=True,
            data=parsed,
            confidence=response.confidence,
            notes=[self._log(
                f"Photo analysis complete (mock={'_mock_notice' in parsed}). "
                f"Likely category: {parsed.get('likely_category', 'unknown')}."
            )],
        )
