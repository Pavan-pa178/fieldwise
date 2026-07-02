

from __future__ import annotations
import json
from .base_agent import BaseAgent, AgentResult
from .llm_client import LLMClient


TRIAGE_CONFIDENCE_THRESHOLD = 0.55


class TriageAgent(BaseAgent):
    name = "triage_agent"

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient()

    def run(self, *, description: str, vision_findings: dict | None = None) -> AgentResult:
        vision_summary = ""
        if vision_findings:
            vision_summary = (
                f"Photo analysis suggests: {vision_findings.get('likely_cause', 'unknown')} "
                f"(category: {vision_findings.get('likely_category', 'unknown')}). "
            )

        prompt = (
            "Triage this crop health case. Classify into exactly one of: "
            "disease, pest, nutrient_deficiency. "
            f"{vision_summary}"
            f"--- FARMER DESCRIPTION START ---\n{description}\n--- FARMER DESCRIPTION END ---"
        )

        response = self.llm.generate(prompt)

        try:
            parsed = json.loads(response.text)
            category = parsed.get("category", "unknown")
        except (json.JSONDecodeError, AttributeError):
            category = "unknown"

        # SAFETY GATE: low confidence -> escalate, don't guess.
        if response.confidence < TRIAGE_CONFIDENCE_THRESHOLD or category == "unknown":
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={"category": "needs_human_expert", "raw_category_guess": category},
                confidence=response.confidence,
                notes=[
                    self._log(
                        f"Confidence {response.confidence} below threshold "
                        f"{TRIAGE_CONFIDENCE_THRESHOLD} — escalating to human expert "
                        "instead of guessing."
                    )
                ],
            )

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={"category": category},
            confidence=response.confidence,
            notes=[self._log(f"Classified case as '{category}' with confidence {response.confidence}.")],
        )
