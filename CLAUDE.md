# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A multi-agent "deep research" pipeline built on the **OpenAI Agents SDK** (`openai-agents`) but pointed at **Google Vertex AI** (Gemini) models through Vertex's OpenAI-compatible endpoint. Given a query, it plans web searches, runs them in parallel, synthesizes a long markdown report, and emails it. Originally adapted from Ed Donner's Agents course lab 4 (`4_lab4.ipynb`, kept as the working reference); the `deep_research/` package is the refactored module form.

## Architecture

The pipeline is orchestrated by `ResearchManager.run()` (`deep_research/research_manager.py`), an async generator that yields status strings and finally the report markdown:

```
query → planner_agent → [search_agent × N in parallel] → writer_agent → email_agent
```

- **`planner_agent`** (`planner_agent.py`) — structured output (`WebSearchPlan`) of N search terms + reasons. `HOW_MANY_SEARCHES` controls N.
- **`search_agent`** (`search_agent.py`) — has a `search_web` `@function_tool` that scrapes DuckDuckGo HTML (`html.duckduckgo.com`) via `requests` + `beautifulsoup4`. `ModelSettings(tool_choice="required")` forces the tool call. This replaces the original lab's paid OpenAI `WebSearchTool`. Searches run concurrently via `asyncio.as_completed`; failed searches return `None` and are dropped.
- **`writer_agent`** (`writer_agent.py`) — structured output (`ReportData`: `short_summary`, `markdown_report`, `follow_up_questions`).
- **`email_agent`** (`email_agent.py`) — `send_email` `@function_tool` sends HTML via SendGrid.

### The Vertex AI integration (most important file: `vertex_client.py`)

All agents import their model objects from `vertex_client.py`, which is the single place that:
- Authenticates via **Google Application Default Credentials** (`google.auth.default()`) — NOT an API key. It refreshes the ADC token and passes it as the `api_key` to an `AsyncOpenAI` client whose `base_url` points at the Vertex `endpoints/openapi` path.
- Exposes two model objects: `vertex_model` (`gemini-2.5-pro`, default) and `vertex_flash_model` (`gemini-2.5-flash`, cheaper/faster). Planner/writer use pro; search/email use flash.
- Calls `set_tracing_disabled(True)` — OpenAI platform tracing is off since we don't use the OpenAI API. (The `trace()`/`gen_trace_id()` calls in `research_manager.py` are no-ops as a result.)

**Token lifetime gotcha:** the ADC token is refreshed once at *module import* (when `make_model` builds the clients), not per request. Long-running processes can hit token expiry.

## Running

There is no wired-up entry point yet (`gradio` is in `requirements.txt` but no app file exists, and `ResearchManager.send_email` is currently commented out). To run, either use the notebook or instantiate `ResearchManager` directly. Modules use **flat sibling imports** (`from search_agent import ...`, no package prefix), so you must run from **inside the `deep_research/` directory**:

```bash
cd deep_research
python -c "import asyncio; from research_manager import ResearchManager; \
  asyncio.run((lambda m: [print(s) async for s in m.run('your query')])(ResearchManager()))"
```

Prerequisites:
- `pip install -r requirements.txt`
- **Google ADC must be configured** before running: `gcloud auth application-default login` (and the project must have Vertex AI enabled).
- `.env` (gitignored) supplies `GCP_PROJECT`, `GCP_LOCATION`, `MODEL_NAME`. Loaded with `load_dotenv(override=True)`.
- Email also needs `SENDGRID_API_KEY` in the environment (not in `.env`), plus editing the hardcoded sender/recipient in `email_agent.py`.

No test suite, linter, or build step is configured.

## Notes for editing

- Adding an agent: build its model from `vertex_client` (`vertex_model` or `vertex_flash_model`) rather than constructing a new client, so auth/token logic stays in one place.
- Structured outputs use Pydantic `BaseModel` + `output_type=`; retrieve with `result.final_output_as(Model)`.
- `email_agent.py` has placeholder sender/recipient addresses that must be set to a SendGrid-verified sender to actually send.
