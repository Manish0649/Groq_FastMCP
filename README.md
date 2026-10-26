# ⚡ Groq + FastMCP + FastAPI with Langfuse Observability

A production-ready AI agent architecture combining **Groq Cloud LLMs**, **FastMCP** tool server, **FastAPI** web framework, and **Langfuse** observability & tracing with a modern web dashboard.

---

## 🎯 Architecture Overview

This project hosts an in-process **FastMCP** tool server inside **FastAPI** with combined lifespans and lets **Groq Cloud** models execute tools via two modes:

| Mode | Who Runs Tools? | Public URL Required? | Best For | Endpoint |
| :--- | :--- | :--- | :--- | :--- |
| **Local Loop** | Your Python process, using Groq `chat.completions` | ❌ No | Development, private tools, local testing | `POST /ask/local` |
| **Remote MCP** | Groq's servers, via the Responses API (beta) | ✅ Yes (HTTPS via ngrok/tunnel) | Production, single-call agents | `POST /ask/remote` |

### 🔍 Integrated Langfuse Observability
Both modes are fully instrumented with **Langfuse**:
- **Agent Traces:** Captures full prompt-to-response lifecycle, timestamps, and overall latency.
- **LLM Generations:** Tracks model parameters, prompt messages, assistant thoughts, token counts (prompt, completion, total), and inference duration.
- **FastMCP Tool Spans:** Records tool arguments, outputs, execution latencies, and error states for each tool (`add`, `multiply`, `get_weather`).
- **Interactive Monitoring Dashboard:** Built-in web UI with live KPI metrics, search, waterfall execution trees, raw JSON payloads, and deep links to Langfuse Cloud!

---

## 📂 Project Structure

```
GROQ_FastMCP/
├── .env.example              # Environment variables template
├── .env                      # Local environment configuration
├── .gitignore                # Git ignore rules
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
├── app/
│   ├── __init__.py
│   ├── config.py             # Loads Groq & Langfuse config from .env
│   ├── main.py               # FastAPI app, FastMCP mount, combined lifespans
│   ├── schemas.py            # Pydantic request & response models
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py         # REST endpoints (/ask/local, /ask/remote, /api/monitoring/*)
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── groq_local.py     # Local agent loop with FastMCP Client & Langfuse tracing
│   │   └── groq_remote.py    # Remote MCP agent via Groq Responses API
│   ├── mcp_server/
│   │   ├── __init__.py
│   │   ├── server.py         # FastMCP instance registering tools
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── math_tools.py # add, multiply
│   │       └── weather_tools.py # get_weather
│   └── monitoring/
│       ├── __init__.py
│       └── tracker.py        # Langfuse client sync and local trace repository
├── streamlit_app.py          # Streamlit Agent Console & Langfuse Monitoring Dashboard
├── scripts/
│   ├── __init__.py
│   └── run_local_agent.py    # CLI entry point to test the agent without HTTP
└── tests/
    ├── __init__.py
    ├── test_tools.py         # In-memory FastMCP tool unit tests
    └── test_api.py           # FastAPI & Langfuse trace integration tests
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites & Installation

```bash
# Clone and navigate to the project directory
cd GROQ_FastMCP

# Create and activate virtual environment (Windows PowerShell)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
copy .env.example .env
```

Edit `.env` with your API keys:

```env
# Groq Cloud API Credentials (https://console.groq.com/keys)
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Remote MCP Public Endpoint (Only required for /ask/remote mode)
MCP_PUBLIC_URL=https://your-tunnel.ngrok-free.app/mcp-server/mcp

# Langfuse Observability (https://cloud.langfuse.com)
LANGFUSE_PUBLIC_KEY=pk-lf-your_public_key
LANGFUSE_SECRET_KEY=sk-lf-your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

> **Note:** If you haven't configured Langfuse or Groq keys yet, you can still start the server and run the **built-in simulation mode** on the frontend to explore the observability dashboard immediately!

### 3. Launch Frontend (Streamlit)

Run the modern Streamlit frontend:

```bash
streamlit run streamlit_app.py
```

Open your browser and navigate to:
👉 **`http://localhost:8501`**

### 4. (Optional) Run FastAPI REST API Server

If you also wish to expose the HTTP REST endpoints (`/ask/local`, `/ask/remote`, `/mcp-server/mcp`):

```bash
uvicorn app.main:app --reload --port 8000
```

👉 **`http://localhost:8000`**

---

## 🖥️ Streamlit & Web Console Overview

The Streamlit app ([`streamlit_app.py`](file:///c:/Fellowship_projects/GROQ_FastMCP/streamlit_app.py)) features:
1. **💬 Agent Playground:**
   - Interactive prompt tester for both Local Loop (`/ask/local`) and Remote MCP (`/ask/remote`) modes.
   - Preset buttons (Weather + Math, Multi-step calculations).
   - Live step-by-step reasoning & tool execution visualizer.
   - Real-time token and latency metrics.
2. **📊 Langfuse Monitoring Dashboard:**
   - 4 Live KPI counters: Total Traces, FastMCP Tool Calls, Average Latency (ms), Total Tokens (Prompt + Completion).
   - Trace Explorer table with mode filter, search, and status badges.
   - **Waterfall Execution Tree:** Visualizes Root Span ➔ Groq LLM Generation ➔ FastMCP Tool Spans ➔ Final Output.
   - Raw JSON payload inspector.
   - Direct link to Langfuse Cloud for deep-dive observability.
3. **🛠️ MCP Tools Registry:**
   - Inspect all FastMCP tools (`add`, `multiply`, `get_weather`) and their JSON Schemas.
4. **⚙️ Config & Setup Guide:**
   - Visual healthcheck indicators for Groq, FastMCP server, and Langfuse connectivity.
2. **Langfuse Monitoring Dashboard (`#monitoring`):**
   - KPI counters: Total Traces, Total Tool Calls, Average Latency (ms), Total Tokens (Prompt + Completion).
   - Trace Explorer table with mode filters, search, and status badges.
   - **Waterfall Execution Tree:** Visualizes Root Span ➔ Groq LLM Generation ➔ FastMCP Tool Spans ➔ Final Output.
   - Raw JSON payload inspector with 1-click clipboard copy.
   - Direct link to Langfuse Cloud for deep-dive observability.
3. **MCP Tools Registry (`#tools`):**
   - Inspect all FastMCP tools (`add`, `multiply`, `get_weather`) and their JSON Schemas.
   - 1-click "Try in Console" buttons.
4. **Config & Setup Guide (`#settings`):**
   - Visual healthcheck indicators for Groq, FastMCP server, and Langfuse connectivity.

---

## 🧪 Testing & CLI Usage

### Running Tests
Execute the automated test suite covering FastMCP tools, API endpoints, and monitoring:

```bash
pytest
```

### CLI Agent Runner
Run queries directly from your terminal:

```bash
python -m scripts.run_local_agent "What is 17 + 25, and what's the weather in Rajpura?"
```

### REST API Examples (cURL)

**Local Agent Loop (`/ask/local`):**
```bash
curl -X POST http://localhost:8000/ask/local \
  -H "Content-Type: application/json" \
  -d '{"question": "What is 17 + 25, and what is the weather in Rajpura?"}'
```

**Remote MCP (`/ask/remote`):**
```bash
# 1. Start tunnel: ngrok http 8000
# 2. Set MCP_PUBLIC_URL=https://<your-ngrok-subdomain>.ngrok-free.app/mcp-server/mcp in .env
# 3. Call endpoint:
curl -X POST http://localhost:8000/ask/remote \
  -H "Content-Type: application/json" \
  -d '{"question": "What is 482 * 19?"}'
```

**Fetch Live Langfuse Monitoring Traces:**
```bash
curl http://localhost:8000/api/monitoring/traces
```

---

## ➕ Adding a New FastMCP Tool

1. Create or add your Python function in `app/mcp_server/tools/`:
   ```python
   def compute_discount(price: float, percentage: float) -> float:
       """Calculate discounted price given original price and percentage."""
       return round(price * (1.0 - percentage / 100.0), 2)
   ```
2. Register it in `app/mcp_server/server.py`:
   ```python
   from app.mcp_server.tools.discount_tools import compute_discount
   mcp.tool(compute_discount)
   ```
3. Restart the server. The tool is automatically detected, exposed to Groq, and tracked in Langfuse!
#   G r o q _ F a s t M C P  
 