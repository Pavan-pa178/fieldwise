# Security & Safety Design

FieldWise gives advice that can affect a real farmer's crop and income, so safety
and security weren't an afterthought — they shaped the architecture. This
document lists every deliberate decision, and where to find it in code.

## 1. Confidence-gated escalation (core safety guarantee)

**The risk:** an LLM that's actually unsure can still *sound* confident. A
confidently-wrong diagnosis is more dangerous than no diagnosis at all,
because the farmer may act on it.

**The mitigation:** every stage that makes a judgment call — triage and
diagnosis — carries an explicit confidence score. If that score falls below
a threshold (`TRIAGE_CONFIDENCE_THRESHOLD` / `DIAGNOSIS_CONFIDENCE_THRESHOLD`),
the system refuses to proceed automatically and instead routes the case to
`needs_human_expert`. No treatment plan, no fabricated diagnosis — just an
honest "this needs a person."

- Code: `agents/triage_agent.py`, `agents/diagnosis_agent.py`
- Tests: `tests/test_pipeline.py::test_low_confidence_escalates_to_human`,
  `::test_unknown_category_escalates`

## 2. Fail-loud on malformed AI output

If the LLM's response can't be parsed into the expected structure (e.g. not
valid JSON), the system treats that the same as low confidence — escalate,
don't guess at what was meant. This protects against an LLM hallucinating a
plausible-looking but structurally broken response.

- Code: `agents/triage_agent.py` (`category == "unknown"` branch)

## 3. No API keys or secrets in source code

- `agents/llm_client.py` reads `GEMINI_API_KEY` strictly from the
  environment at call time, never from a hardcoded constant.
- If `FIELDWISE_LLM_MODE=gemini` is set but the key is missing, the client
  raises a `RuntimeError` immediately rather than silently falling back to
  mock mode (which could mislead someone into thinking they're getting real
  AI analysis when they're not).
- `.gitignore` excludes `.env` and any `*.env` file; only `.env.example`
  (with no real values) is tracked.
- Test: `tests/test_pipeline.py::test_gemini_mode_requires_api_key`

## 4. Data minimization for farmer identity

- `farmer_id` is documented and expected to be a pseudonymous identifier
  (e.g. a hashed phone number or app-assigned UUID) — not a real name —
  see the docstring in `agents/followup_agent.py`.
- Case history (`data/case_history.json`) stores only category, diagnosis,
  and dates — no raw personal description text, no images, no location
  more precise than the region string the user provides.

## 5. Uploaded photos are not retained

The Streamlit app (`web/app.py`) writes an uploaded photo to a temporary
file only for the duration of processing, then deletes it (`os.unlink`)
immediately after the pipeline finishes — see the `image_path` cleanup in
`main()`. No farmer's photo is persisted to disk after their session ends.

## 6. Single agent owns persistence

Only `FollowUpAgent` writes to `data/case_history.json`. No other agent
touches disk directly. This keeps the attack surface and audit trail small:
if something unexpected ends up in case history, there's exactly one place
to look.

## 7. MCP tool isolation

The local-supplier lookup (`mcp_server/market_server.py`) is a separate
process/module from the reasoning agents. It only ever receives a
diagnosis string, category, and region — never the farmer's raw
description, photo, or ID. A compromised or buggy market data source
cannot leak farmer-identifying information, because it never receives any.

## 8. Defensive guards between pipeline stages

`DiagnosisAgent` and `ResourceAgent` both explicitly check for and refuse to
process a case already marked `needs_human_expert`, even though the
orchestrator should never call them in that state. This belt-and-suspenders
check protects against future refactors accidentally bypassing the
orchestrator's escalation logic.

## What this project does *not* claim

- This is a decision-support tool, not a replacement for a licensed
  agronomist. The escalation path exists precisely because we don't claim
  100% diagnostic reliability.
- Mock mode is clearly labeled in the UI (`web/app.py` shows an explicit
  "Running in MOCK mode" banner) so nobody mistakes demo output for a real
  AI diagnosis.
