from __future__ import annotations
import json
from .base_agent import BaseAgent, AgentResult
from .llm_client import LLMClient

DIAGNOSIS_CONFIDENCE_THRESHOLD = 0.5


class DiagnosisAgent(BaseAgent):
    name = "diagnosis_agent"

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient()

    def run(
        self,
        *,
        category: str,
        description: str,
        vision_findings: dict | None = None,
    ) -> AgentResult:
        if category == "needs_human_expert":
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                notes=[self._log("Skipped — case was already escalated by triage.")],
            )

        vision_summary = ""
        if vision_findings:
            vision_summary = f"Visible symptoms from photo: {vision_findings.get('visible_symptoms', 'n/a')}. "

        prompt = (
            f"Diagnose this {category} case in detail. "
            f"{vision_summary}"
            f"Farmer's description: {description}. "
            "Return the most likely specific cause and a plain-language explanation "
            "a smallholder farmer can understand."
        )

        response = self.llm.generate(prompt)

        try:
            parsed = json.loads(response.text)
        except (json.JSONDecodeError, AttributeError):
            parsed = {"diagnosis": "unable to parse", "explanation": response.text}

        if response.confidence < DIAGNOSIS_CONFIDENCE_THRESHOLD:
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={"category": "needs_human_expert", "partial_diagnosis": parsed},
                confidence=response.confidence,
                notes=[self._log(
                    f"Diagnosis confidence {response.confidence} too low — "
                    "escalating instead of issuing a treatment plan."
                )],
            )

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                "diagnosis": parsed.get("diagnosis", "unknown"),
                "explanation": parsed.get("explanation", ""),
                "category": category,
            },
            confidence=response.confidence,
            notes=[self._log(f"Diagnosed: {parsed.get('diagnosis', 'unknown')}")],
        )
