# FieldWise Architecture

## System overview

```
                              ┌─────────────────────┐
                              │   User (web or CLI)  │
                              │  description + photo │
                              └──────────┬───────────┘
                                         │
                              ┌──────────▼───────────┐
                              │  FieldWiseOrchestrator│
                              │  (agents/orchestrator)│
                              └──────────┬───────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        │                                │                                │
        ▼                                ▼                                ▼
┌───────────────┐              ┌───────────────────┐            ┌──────────────────┐
│  VisionAgent   │   findings   │   TriageAgent      │  category  │  DiagnosisAgent   │
│ (photo, optional)─────────────▶ confidence-gated    ├───────────▶  confidence-gated │
│               │              │  classification     │            │  cause + explain  │
└───────────────┘              └─────────┬───────────┘            └─────────┬────────┘
                                          │ low confidence                  │ low confidence
                                          ▼                                 ▼
                                 ┌──────────────────┐            ┌──────────────────┐
                                 │  needs_human_     │◀───────────┤  needs_human_     │
                                 │  expert (STOP)    │            │  expert (STOP)    │
                                 └──────────────────┘            └─────────┬────────┘
                                                                            │ ok
                                                                            ▼
                                                                 ┌──────────────────────┐
                                                                 │   ResourceAgent        │
                                                                 │   --MCP--▶ market_server│
                                                                 │   find_local_treatment │
                                                                 └─────────┬────────────┘
                                                                           │
                                                                           ▼
                                                                 ┌──────────────────────┐
                                                                 │   FollowUpAgent        │
                                                                 │   schedule + log       │
                                                                 │   case_history.json    │
                                                                 └─────────┬────────────┘
                                                                           │
                                                                           ▼
                                                                 ┌──────────────────────┐
                                                                 │     CaseReport         │
                                                                 │  → Streamlit / CLI     │
                                                                 └──────────────────────┘
```

## Why multiple agents instead of one big prompt

Each stage has a genuinely different job and failure mode:

| Agent | Job | Why separate |
|---|---|---|
| VisionAgent | Read a photo | Different modality, different cost/latency, optional entirely |
| TriageAgent | Bucket the case | Cheap, fast classification; owns the first safety gate |
| DiagnosisAgent | Name the specific cause | Needs deeper domain reasoning; owns the second safety gate |
| ResourceAgent | Make it locally actionable | Talks to an external tool (MCP), not the LLM at all |
| FollowUpAgent | Schedule + persist | Owns all disk writes — single point of audit |

Splitting these means each agent can be improved, swapped, or replaced (e.g.
plugging in a real plant-disease vision model for VisionAgent) without
touching the others, and the two safety gates (triage, diagnosis) are
independently testable.

## Mapping to Google ADK

This project implements the control flow in plain Python
(`agents/orchestrator.py`) so it runs with zero cloud dependency for
development and grading. The structure maps directly onto ADK's
agent/tool/graph model:

- Each `BaseAgent` subclass → an ADK `Agent` with a declared instruction
  and tool set.
- `ResourceAgent`'s call into `mcp_server/mcp_client.py` → an ADK `Tool`
  backed by an MCP server connection (ADK has first-class MCP tool support).
- `FieldWiseOrchestrator.process_case()`'s sequential-with-branches control
  flow → an ADK graph workflow with conditional edges on the
  `needs_human_expert` branch.

Porting this to live ADK + Gemini is mechanical: wrap each agent class in
`google.adk.Agent`, register `find_local_treatment` as an MCP-backed tool,
and replace `LLMClient(mode="mock")` with `mode="gemini"` (see
`agents/llm_client.py`).

## Deployability

No live endpoint is required for judging (per the competition rules), but
FieldWise is designed to deploy without architecture changes:

- **Web app** (`web/app.py`): deployable as-is to Streamlit Community Cloud,
  or containerized and deployed to **Google Cloud Run** — a single
  `Dockerfile` wrapping `streamlit run web/app.py` is sufficient, since the
  app has no server-side state beyond the local JSON case history (which
  would move to Firestore/Cloud SQL for a multi-instance deployment).
- **MCP server** (`mcp_server/market_server.py`): runs as its own process;
  in production this would be deployed as a long-running service (e.g. Cloud
  Run job or a small VM) rather than spawned per-request, with the
  `local_suppliers.json` mock data replaced by a real supplier API or
  government open-data feed — the tool's *interface*
  (`find_local_treatment(diagnosis, category, region)`) would not change.
- **CLI / Agent skill** (`cli/fieldwise_cli.py`): usable as-is in a cron job
  or batch pipeline for an extension office processing many cases at once.
- **Real-world entry point:** in a full deployment, an SMS/WhatsApp gateway
  (e.g. Twilio) would sit in front of the orchestrator so farmers never need
  a smartphone app — they'd text a photo and description, and FieldWise
  would reply with the same `CaseReport` content rendered as a text message.

## Data flow & storage

- Uploaded photos: processed in-memory/temp-file only, deleted immediately
  after the pipeline runs (see `web/app.py`).
- Case history: append-only JSON file (`data/case_history.json`) for this
  demo; would become a proper database (Firestore/Cloud SQL) in production
  to support concurrent users and querying by farmer over time.
- Supplier data: static JSON (`data/local_suppliers.json`) for this demo;
  swappable for a live API without touching agent code (see
  `mcp_server/market_server.py`).
