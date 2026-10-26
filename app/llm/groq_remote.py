"""Remote MCP Agent using Groq Responses API with Langfuse Monitoring."""
import time
from typing import Any, Tuple
from openai import OpenAI
from app import config
from app.monitoring.tracker import monitoring_tracker


def get_openai_client() -> OpenAI:
    """Initialize OpenAI client pointing to Groq's endpoint."""
    api_key = config.GROQ_API_KEY or "dummy_key_for_init"
    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )


def ask_remote_with_trace(question: str) -> Tuple[str, Any]:
    """Execute agent call via Groq Responses API with Langfuse instrumentation."""
    trace = monitoring_tracker.start_trace(
        name="groq_fastmcp_ask_remote",
        mode="remote",
        question=question,
    )

    if not config.is_groq_configured():
        msg = (
            "GROQ_API_KEY is not set. Please set a valid GROQ_API_KEY in your .env file. "
            "Get a free API key at https://console.groq.com/keys."
        )
        trace.finish(error=msg)
        return msg, trace

    if not config.MCP_PUBLIC_URL or "your-host.example.com" in config.MCP_PUBLIC_URL:
        msg = (
            "MCP_PUBLIC_URL must be configured with a public HTTPS URL (e.g., via ngrok or cloudflared) "
            "for Groq Cloud to connect to your MCP server. Current value: "
            f"'{config.MCP_PUBLIC_URL}'"
        )
        trace.finish(error=msg)
        return msg, trace

    client = get_openai_client()

    try:
        t_start = time.time()

        # Groq Responses API with remote MCP server definition
        resp = client.responses.create(
            model=config.GROQ_MODEL,
            input=question,
            tools=[{
                "type": "mcp",
                "server_label": "my_tools",
                "server_url": config.MCP_PUBLIC_URL,
                "require_approval": "never",
            }],
        )
        t_duration = (time.time() - t_start) * 1000

        output_text = getattr(resp, "output_text", None) or str(resp)

        # Log completion to Langfuse
        trace.log_llm_call(
            model=config.GROQ_MODEL,
            messages=[{"role": "user", "content": question}],
            response_content=output_text,
            duration_ms=t_duration,
        )

        trace.finish(answer=output_text)
        return output_text, trace

    except Exception as e:
        error_msg = f"Remote MCP Error: {str(e)}"
        trace.finish(error=error_msg)
        return error_msg, trace


def ask_remote(question: str) -> str:
    """Standard signature as specified in project documentation."""
    answer, _ = ask_remote_with_trace(question)
    return answer
