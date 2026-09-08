# E-Commerce Sales Analytics Chatbot & Pinnable Dashboard

An intelligent E-Commerce Sales Analytics Chatbot and Chart Builder with a Pinnable Dashboard built on the Brazilian E-Commerce Public Dataset by Olist (~100k real orders across 8 relational tables).

---

## Features
- **MCP Tool Architecture**: Exposes analytics tools over Olist SQL dataset via the official Python `mcp` SDK (`FastMCP`).
- **Dual LLM & Rule Fallback Agent (`ILLMAgent`)**: Switch seamlessly between LLM-backed native tool calling and keyword-based rule fallback using `AGENT_MODE=llm|fallback`.
- **Chart Selector Engine**: Recommends appropriate Chart.js charts (Line, Horizontal Bar, Donut, Dual-Axis, Scatter, Stacked Bar) with 1-sentence data insights and justifications.
- **Pinnable Dashboard**: Persistent dashboard pin board with refresh change/diff detection.
- **Sample & Multi-Tool Queries**: Full coverage of single-tool queries, joint multi-tool queries, and guardrail handling (out-of-bounds queries, empty results, tool timeouts).

---

## Quick Start (Docker Compose)

1. **Clone repository and set API key**:
   ```bash
   cp .env.example .env
   # Add your GROQ_API_KEY (or OPENAI_API_KEY) in .env
   # Example: GROQ_API_KEY=gsk_...
   ```

2. **Run with Docker Compose**:
   ```bash
   docker compose up --build
   ```

3. **Access Application**:
   Open browser at `http://localhost:8000`.

---

## Development Setup (uv)

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Run database loader (automatic on startup or manual)**:
   ```bash
   uv run python -m src.database.loader
   ```

3. **Start local server**:
   ```bash
   uv run uvicorn src.main:app --reload --port 8000
   ```

4. **Run tests**:
   ```bash
   uv run pytest
   ```

---

## Design Decisions

### Chart Type Selection Logic
- **Single metric over time**: Line chart (`line`)
- **Two metrics over same time axis**: Dual-axis line chart (`line` with 2 y-axes)
- **Ranked list (Top N)**: Horizontal bar chart (`bar`, `indexAxis: 'y'`)
- **Category comparison**: Vertical bar chart (`bar`)
- **Part-to-whole share**: Donut chart (`doughnut`)
- **Correlation**: Scatter plot (`scatter`)
- **Rating score distribution**: Stacked horizontal bar chart

### Refresh Diff Detection Engine
When a pinned chart is refreshed, the backend re-executes the original tool call against current dataset state, compares metrics against stored baseline values, and alerts if metric shifts exceed 5%.

### Fallback Agent Behavior
When `AGENT_MODE=fallback` or LLM key is absent/timing out, `RuleBasedFallbackAgent` extracts date ranges, entity filters, and ranking keywords directly, queries MCP tools, and constructs Chart.js configs deterministically.
