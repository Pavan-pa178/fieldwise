# 🌱 FieldWise

**A multi-agent crop health advisor for smallholder farmers.**

Built for the *AI Agents: Intensive Vibe Coding Capstone Project* — **Agents for Good** track.

---

## The problem

Smallholder farmers often can't access an agronomist when a crop starts
showing signs of disease, pest damage, or nutrient deficiency. By the time
expert help arrives — if it ever does — yield is already lost. Generic
internet advice rarely accounts for what treatments are actually available
and affordable nearby.

## The solution

FieldWise is a multi-agent pipeline that takes a farmer's description (and
optionally a photo) of a sick crop, and returns:

1. A **diagnosis** in plain language.
2. A **locally actionable treatment plan** — real nearby suppliers, products,
   and approximate prices, not generic "use a fungicide" advice.
3. A **follow-up schedule** so the farmer knows when to check again.

Critically, if the system isn't confident enough in its diagnosis, **it says
so and escalates to a human expert instead of guessing.** That safety
behavior is a first-class part of the architecture, not an afterthought —
see [`docs/SECURITY.md`](docs/SECURITY.md).

## Why agents (not one big prompt)

Triage, diagnosis, local resourcing, and follow-up scheduling are genuinely
different jobs with different failure modes. Splitting them into specialized
agents means:

- The two safety/confidence checks (triage, diagnosis) are isolated and
  independently testable.
- The "find local treatment" step calls a real tool over **MCP**, not a
  hardcoded database import — meaning that data source can be swapped for
  a live supplier API without touching any agent's reasoning code.
- Each agent can be improved or swapped independently (e.g. plugging in a
  dedicated plant-disease vision model later) without rewriting the rest.

Full architecture diagram and reasoning: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## Key concepts demonstrated

| Concept | Where |
|---|---|
| Multi-agent system (ADK-style design) | `agents/` — 5 agents + orchestrator |
| MCP Server | `mcp_server/market_server.py` (real MCP tool: `find_local_treatment`) |
| Security features | Confidence-gated escalation, no hardcoded secrets, data minimization — see `docs/SECURITY.md` |
| Deployability | See "Deployability" section in `docs/ARCHITECTURE.md` |
| Agent skill (CLI) | `cli/fieldwise_cli.py` — single-case, batch, and history modes |
| Antigravity | Used to scaffold and iterate on this implementation (see demo video) |

## Project structure

```
fieldwise/
├── agents/
│   ├── llm_client.py        # LLM abstraction: mock mode (free/offline) or Gemini mode
│   ├── base_agent.py        # Shared agent contract
│   ├── vision_agent.py      # Photo analysis (optional input)
│   ├── triage_agent.py      # Classifies case + first safety gate
│   ├── diagnosis_agent.py   # Specific diagnosis + second safety gate
│   ├── resource_agent.py    # Calls MCP tool for local treatment options
│   ├── followup_agent.py    # Schedules check-in, logs case history
│   └── orchestrator.py      # Coordinates the full pipeline
├── mcp_server/
│   ├── market_server.py     # Real MCP server exposing find_local_treatment
│   └── mcp_client.py        # Client wrapper (subprocess MCP, with safe fallback)
├── cli/
│   └── fieldwise_cli.py     # Agent skill / CLI: diagnose, batch, history
├── web/
│   └── app.py                # Streamlit front end
├── data/
│   ├── local_suppliers.json  # Mock supplier/market data backing the MCP tool
│   └── sample_batch_cases.json
├── tests/
│   └── test_pipeline.py      # 11 tests covering happy paths + safety paths
├── docs/
│   ├── ARCHITECTURE.md
│   └── SECURITY.md
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

```bash
git clone <your-repo-url>
cd fieldwise
pip install -r requirements.txt
```

No API key is required to run FieldWise. It defaults to **mock mode** —
fully offline, free, deterministic — which is sufficient to explore the
entire multi-agent pipeline, the MCP tool, and the safety/escalation logic.

### Run the web app

```bash
streamlit run web/app.py
```

Open the local URL it prints (usually `http://localhost:8501`).

### Run the CLI (Agent skill)

```bash
# Single case
python cli/fieldwise_cli.py diagnose \
  --farmer-id demo_farmer \
  --description "Dark brown spots with yellow rings on tomato leaves" \
  --region vijayawada

# Batch processing
python cli/fieldwise_cli.py batch \
  --input data/sample_batch_cases.json \
  --output data/batch_results.json

# View a farmer's case history
python cli/fieldwise_cli.py history --farmer-id demo_farmer
```

### Run the tests

```bash
python -m pytest tests/ -v
```

### Switching to live Gemini-powered diagnosis (optional)

By default everything above runs on deterministic mock responses — zero
cost, zero setup. To use real AI:

```bash
cp .env.example .env
# edit .env: set FIELDWISE_LLM_MODE=gemini and add your GEMINI_API_KEY
# get a free key at https://aistudio.google.com/app/apikey
export $(cat .env | xargs)
pip install google-generativeai pillow
streamlit run web/app.py
```

No agent code changes — see `agents/llm_client.py` for how the swap works.

🚨 Never commit a real `.env` file or hardcode an API key. `.gitignore`
already excludes `.env`.

## Testing the MCP server independently

```bash
python -m mcp_server.market_server
```

This starts the MCP server over stdio, the standard transport for local MCP
tool servers. `mcp_client.py` automatically falls back to an in-process call
of the same tool logic if the `mcp` package isn't installed, so the rest of
the project keeps working either way — but install `mcp` (in
`requirements.txt`) to exercise the real protocol.

## Project journey / design notes

This project deliberately keeps the LLM layer fully mockable from day one
(`agents/llm_client.py`) so the entire multi-agent architecture, the MCP
integration, and — most importantly — the safety escalation logic could be
built, tested, and demoed without needing a paid API key or worrying about
rate limits during development. Every place a real Gemini call would slot in
is marked and isolated to a single file.

## License

Built for the Kaggle AI Agents Capstone Project. See competition rules for
submission terms.
