from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentResult:
    agent_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    notes: List[str] = field(default_factory=list)


class BaseAgent(ABC):
    

    name: str = "base_agent"

    @abstractmethod
    def run(self, **kwargs) -> AgentResult:
        ...

    def _log(self, message: str) -> str:
        return f"[{self.name}] {message}"
