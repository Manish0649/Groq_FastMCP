# Groq + FastMCP + FastAPI with Langfuse

## About the Project

This project is built using Groq, FastMCP, FastAPI, and Langfuse to create an AI agent that can answer questions and use tools when needed.

The project also includes a Streamlit frontend where users can interact with the agent, test different queries, view tool executions, and monitor traces.

I have implemented two ways to run the agent:

- **Local Agent:** The Python application handles tool execution using the Groq Chat Completions API.
- **Remote MCP:** Groq uses the Responses API to access tools through a publicly accessible MCP server.

Langfuse is integrated to track LLM calls, tool executions, token usage, response time, and errors.

## Technologies Used

- **Python** – Main programming language
- **Groq API** – To interact with LLMs
- **FastMCP** – To create and manage MCP tools
- **FastAPI** – To build REST APIs
- **Streamlit** – To build the frontend
- **Langfuse** – To monitor and trace agent execution
- **Pydantic** – To validate request and response data
- **Pytest** – To test the application

## Project Structure

```text
GROQ_FastMCP/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── schemas.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── groq_local.py
│   │   └── groq_remote.py
│   ├── mcp_server/
│   │   ├── __init__.py
│   │   ├── server.py
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── math_tools.py
│   │       └── weather_tools.py
│   └── monitoring/
│       ├── __init__.py
│       └── tracker.py
├── streamlit_app.py
├── scripts/
│   ├── __init__.py
│   └── run_local_agent.py
└── tests/
    ├── __init__.py
    ├── test_tools.py
    └── test_api.py
```

## Features

### 1. AI Agent

The agent uses a Groq language model to understand user queries and decide when to call a tool.

Currently, the available tools are:

- `add` – Adds two numbers.
- `multiply` – Multiplies two numbers.
- `get_weather` – Retrieves weather information based on the implemented tool logic.

### 2. Local Agent Mode

In this mode, the Python application manages the agent loop. It sends the user's query to Groq, executes the selected tools through FastMCP, and sends the results back to the model.

This mode is useful for local development and testing without exposing the MCP server to the internet.

Endpoint: `POST /ask/local`

### 3. Remote MCP Mode

In this mode, Groq accesses the MCP server through a public HTTPS endpoint using the Responses API.

A public tunnel, such as ngrok, is required when running the MCP server locally.

Endpoint: `POST /ask/remote`

**Note:** This mode depends on the availability and compatibility of the Groq Responses API and its remote MCP support.

### 4. Langfuse Monitoring

Langfuse is used to monitor the agent's execution and understand how requests are processed.

The monitoring features include:

- Agent traces and execution details
- LLM calls and model information
- Tool inputs, outputs, and execution time
- Token usage and response latency
- Errors during execution

The project also includes a monitoring dashboard in Streamlit to explore traces and view execution details.

### 5. Streamlit Frontend

The Streamlit application provides a simple interface to interact with the agent.

It includes:

- A chat interface for testing queries
- Options to select local or remote mode
- Example prompts for maths and weather queries
- Tool execution details
- Token usage and latency information
- A Langfuse monitoring dashboard
- A registry of available MCP tools
- Configuration and setup information

A simulation mode is also included in the frontend for exploring the dashboard without connecting to the live services, where supported by the implementation.

## Getting Started

### Step 1: Clone the Repository

```bash
git clone <your-repository-url>
cd GROQ_FastMCP
```

Replace `<your-repository-url>` with your repository URL.

### Step 2: Create a Virtual Environment

For Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If activation is blocked by your PowerShell execution policy, use the appropriate environment activation method for your system.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file by copying the example file:

```powershell
Copy-Item .env.example .env
```

Add your API keys and configuration to the `.env` file:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

MCP_PUBLIC_URL=https://your-tunnel.ngrok-free.app/mcp-server/mcp

LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

Get your Groq API key from [Groq Console](https://console.groq.com/keys).

For tracing, create a project in [Langfuse Cloud](https://cloud.langfuse.com) and configure the corresponding keys.

The `MCP_PUBLIC_URL` variable is needed only for remote MCP mode.

**Important:** Keep your `.env` file private and never upload API keys to GitHub.

### Step 5: Run the Streamlit Application

```bash
streamlit run streamlit_app.py
```

Open the following URL in your browser:

```text
http://localhost:8501
```

### Step 6: Run the FastAPI Server

Open another terminal, activate the virtual environment, and run:

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at:

```text
http://localhost:8000
```

You can also access the FastAPI Swagger documentation at:

```text
http://localhost:8000/docs
```

## Testing the API

### Local Agent

Send a POST request to `/ask/local` with a question.

Example using cURL:

```bash
curl -X POST http://localhost:8000/ask/local \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What is 17 + 25?\"}"
```

### Remote MCP

First, start ngrok in a separate terminal:

```bash
ngrok http 8000
```

Copy the HTTPS URL generated by ngrok and update `MCP_PUBLIC_URL` in the `.env` file. Make sure the URL points to the MCP endpoint configured in the application.

Then send a request:

```bash
curl -X POST http://localhost:8000/ask/remote \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What is 482 * 19?\"}"
```

Remote mode requires valid credentials, a publicly accessible MCP endpoint, and support for the configured API.

## Running the CLI Agent

The local agent can also be tested directly from the terminal without sending an HTTP request.

```bash
python -m scripts.run_local_agent "What is 17 + 25?"
```

## Running Tests

Run the test suite using Pytest:

```bash
pytest
```

The tests cover the MCP tools, API endpoints, and monitoring-related functionality implemented in the project.

## Adding a New MCP Tool

New tools can be added to the project by following these steps.

### Step 1: Create the Tool

For example, create `app/mcp_server/tools/discount_tools.py`:

```python
def compute_discount(price: float, percentage: float) -> float:
    """Calculate the discounted price."""
    return round(price * (1 - percentage / 100), 2)
```

### Step 2: Register the Tool

Import the function in `app/mcp_server/server.py` and register it with the FastMCP instance:

```python
from app.mcp_server.tools.discount_tools import compute_discount

mcp.tool(compute_discount)
```

Follow the same registration pattern used by the existing tools in the project.

### Step 3: Test the Tool

Restart the application and test the new tool with a suitable query. You can also add unit tests to check whether it returns the expected result.

## What I Learned

While working on this project, I got practical experience with:

- Creating MCP tools using FastMCP
- Connecting an LLM to external tools
- Building REST APIs with FastAPI
- Working with Groq-hosted language models
- Understanding the difference between local and remote tool execution
- Integrating Langfuse for LLM observability
- Building an interactive interface with Streamlit
- Testing Python applications using Pytest

## Future Improvements

Some improvements that can be made to the project are:

- Add more useful MCP tools.
- Improve error handling and request validation.
- Add authentication and rate limiting to the API.
- Improve the monitoring dashboard.
- Add more automated tests.
- Deploy the application so it can be accessed online.

## Conclusion

This project combines FastMCP, Groq, FastAPI, and Langfuse to demonstrate how an AI agent can use tools and how its execution can be monitored.

It was also a way to explore MCP-based tool integration, API development, and observability in a single application.
