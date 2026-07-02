from __future__ import annotations
import os
import sys
import json
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.orchestrator import FieldWiseOrchestrator
from agents.llm_client import LLMClient, LLMResponse
from agents.triage_agent import TriageAgent, TRIAGE_CONFIDENCE_THRESHOLD
from mcp_server.market_server import find_local_treatment


def test_disease_case_end_to_end():

    orchestrator = FieldWiseOrchestrator()
    report = orchestrator.process_case(
        description="Dark brown spots with yellow rings on tomato leaves, fungal looking",
        farmer_id="test_farmer_disease",
        region="vijayawada",
    )
    assert report.escalated is False
    assert report.category == "disease"
    assert report.diagnosis is not None
    assert len(report.treatment_options) > 0
    assert report.case_id is not None


def test_pest_case_end_to_end():
    orchestrator = FieldWiseOrchestrator()
    report = orchestrator.process_case(
        description="Small green insects clustered under leaves, sticky residue, leaves curling",
        farmer_id="test_farmer_pest",
        region="vijayawada",
    )
    assert report.escalated is False
    assert report.category == "pest"


def test_nutrient_case_end_to_end():
    orchestrator = FieldWiseOrchestrator()
    report = orchestrator.process_case(
        description="Older leaves turning pale yellow between veins, plant looks stunted",
        farmer_id="test_farmer_nutrient",
        region="vijayawada",
    )
    assert report.escalated is False
    assert report.category == "nutrient_deficiency"


def test_low_confidence_escalates_to_human():

    orchestrator = FieldWiseOrchestrator()
    low_conf_response = LLMResponse(
        text=json.dumps({"category": "disease"}),
        confidence=TRIAGE_CONFIDENCE_THRESHOLD - 0.1,
    )
    with patch.object(orchestrator.triage_agent.llm, "generate", return_value=low_conf_response):
        report = orchestrator.process_case(
            description="ambiguous symptoms",
            farmer_id="test_farmer_lowconf",
            region="vijayawada",
        )
    assert report.escalated is True
    assert report.category == "needs_human_expert"
    assert report.diagnosis is None  # must NOT fabricate a diagnosis


def test_unknown_category_escalates():

    orchestrator = FieldWiseOrchestrator()
    garbage_response = LLMResponse(text="not valid json", confidence=0.9)
    with patch.object(orchestrator.triage_agent.llm, "generate", return_value=garbage_response):
        report = orchestrator.process_case(
            description="test",
            farmer_id="test_farmer_garbage",
            region="vijayawada",
        )
    assert report.escalated is True


def test_mcp_tool_returns_options_for_known_region():
    result = find_local_treatment(diagnosis="Early blight", category="disease", region="vijayawada")
    assert "options" in result
    assert len(result["options"]) > 0
    assert all("supplier_name" in opt for opt in result["options"])


def test_mcp_tool_falls_back_for_unknown_region():

    result = find_local_treatment(diagnosis="Early blight", category="disease", region="some_unknown_region")
    assert "options" in result
    assert len(result["options"]) > 0


def test_mcp_tool_no_options_for_unsupported_category():
    result = find_local_treatment(diagnosis="X", category="not_a_real_category", region="vijayawada")
    assert result["options"] == []


def test_llm_client_mock_mode_default():

    client = LLMClient()
    assert client.mode == "mock"
    response = client.generate("Triage this case. Farmer description: aphids on leaves")
    assert response.text
    assert 0.0 <= response.confidence <= 1.0


def test_llm_client_rejects_invalid_mode():
    try:
        LLMClient(mode="not_a_real_mode")
        assert False, "Expected ValueError for invalid mode"
    except ValueError:
        pass


def test_gemini_mode_requires_api_key(monkeypatch):

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    try:
        LLMClient(mode="gemini")
        assert False, "Expected RuntimeError when GEMINI_API_KEY is missing"
    except RuntimeError as e:
        assert "GEMINI_API_KEY" in str(e)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
