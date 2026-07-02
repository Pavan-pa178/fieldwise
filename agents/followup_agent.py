from __future__ import annotations
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from .base_agent import BaseAgent, AgentResult
from .llm_client import LLMClient

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "case_history.json")


class FollowUpAgent(BaseAgent):
    name = "followup_agent"

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient()

    def run(self, *, case_summary: dict, farmer_id: str) -> AgentResult:
        prompt = (
            f"Given this diagnosis: {case_summary.get('diagnosis', 'unknown')}, "
            "schedule an appropriate follow-up check-in in days."
        )
        response = self.llm.generate(prompt)

        try:
            parsed = json.loads(response.text)
            days = int(parsed.get("next_check_days", 5))
        except (json.JSONDecodeError, AttributeError, ValueError, TypeError):
            days = 5

        next_check_date = (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()

        case_record = {
            "case_id": str(uuid.uuid4())[:8],
            "farmer_id": farmer_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": case_summary.get("category"),
            "diagnosis": case_summary.get("diagnosis"),
            "next_check_date": next_check_date,
        }

        self._append_to_history(case_record)

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={"next_check_date": next_check_date, "case_id": case_record["case_id"]},
            confidence=0.9,
            notes=[self._log(f"Scheduled follow-up for {next_check_date}; case logged as {case_record['case_id']}.")],
        )

    @staticmethod
    def _append_to_history(record: dict) -> None:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                try:
                    history = json.load(f)
                except json.JSONDecodeError:
                    history = []
        history.append(record)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
