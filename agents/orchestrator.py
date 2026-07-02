from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from .vision_agent import VisionAgent
from .triage_agent import TriageAgent
from .diagnosis_agent import DiagnosisAgent
from .resource_agent import ResourceAgent
from .followup_agent import FollowUpAgent
from .llm_client import LLMClient
from mcp_server.mcp_client import MCPClient


@dataclass
class CaseReport:

    escalated: bool
    category: str
    diagnosis: Optional[str] = None
    explanation: Optional[str] = None
    treatment_options: list = field(default_factory=list)
    next_check_date: Optional[str] = None
    case_id: Optional[str] = None
    trace: list = field(default_factory=list)  # human-readable agent log, for transparency


class FieldWiseOrchestrator:
    def __init__(self, llm_mode: Optional[str] = None):
        llm = LLMClient(mode=llm_mode)
        mcp = MCPClient()

        self.vision_agent = VisionAgent(llm_client=llm)
        self.triage_agent = TriageAgent(llm_client=llm)
        self.diagnosis_agent = DiagnosisAgent(llm_client=llm)
        self.resource_agent = ResourceAgent(mcp_client=mcp)
        self.followup_agent = FollowUpAgent(llm_client=llm)

    def process_case(
        self,
        *,
        description: str,
        farmer_id: str,
        region: str = "default",
        image_path: Optional[str] = None,
    ) -> CaseReport:
        trace = []

        # Step 1: Vision (optional)
        vision_findings = None
        if image_path:
            vision_result = self.vision_agent.run(image_path=image_path)
            vision_findings = vision_result.data
            trace.extend(vision_result.notes)

        # Step 2: Triage
        triage_result = self.triage_agent.run(description=description, vision_findings=vision_findings)
        trace.extend(triage_result.notes)
        category = triage_result.data.get("category", "needs_human_expert")

        if category == "needs_human_expert":
            return CaseReport(
                escalated=True,
                category=category,
                trace=trace,
            )

        # Step 3: Diagnosis
        diagnosis_result = self.diagnosis_agent.run(
            category=category, description=description, vision_findings=vision_findings
        )
        trace.extend(diagnosis_result.notes)

        if diagnosis_result.data.get("category") == "needs_human_expert":
            return CaseReport(escalated=True, category="needs_human_expert", trace=trace)

        diagnosis = diagnosis_result.data.get("diagnosis", "unknown")
        explanation = diagnosis_result.data.get("explanation", "")

        # Step 4: Local resourcing (via MCP)
        resource_result = self.resource_agent.run(
            diagnosis=diagnosis, category=category, region=region
        )
        trace.extend(resource_result.notes)

        # Step 5: Follow-up scheduling + history logging
        followup_result = self.followup_agent.run(
            case_summary={"category": category, "diagnosis": diagnosis},
            farmer_id=farmer_id,
        )
        trace.extend(followup_result.notes)

        return CaseReport(
            escalated=False,
            category=category,
            diagnosis=diagnosis,
            explanation=explanation,
            treatment_options=resource_result.data.get("options", []),
            next_check_date=followup_result.data.get("next_check_date"),
            case_id=followup_result.data.get("case_id"),
            trace=trace,
        )
