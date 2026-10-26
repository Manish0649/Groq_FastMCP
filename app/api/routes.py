"""FastAPI routes for agent queries, FastMCP tool introspection, and Langfuse monitoring."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastmcp import Client

from app import config
from app.llm.groq_local import ask_local_with_trace
from app.llm.groq_remote import ask_remote_with_trace
from app.mcp_server.server import mcp
from app.monitoring.tracker import monitoring_tracker
from app.schemas import AskRequest, AskResponse, ToolInfo

router = APIRouter()


@router.get("/health")
def health() -> Dict[str, bool]:
    """Healthcheck endpoint."""
    return {"ok": True}


@router.post("/ask/local", response_model=AskResponse)
async def ask_local_route(body: AskRequest) -> AskResponse:
    """Agent loop running tools locally via FastMCP and Groq chat completions."""
    answer, trace = await ask_local_with_trace(body.question)
    return AskResponse(
        answer=answer,
        trace_id=trace.trace_id if trace else None,
        duration_ms=trace.duration_ms if trace else None,
        tool_calls_count=len(trace.tool_calls) if trace else 0,
    )


@router.post("/ask/remote", response_model=AskResponse)
def ask_remote_route(body: AskRequest) -> AskResponse:
    """Agent loop where Groq Cloud servers connect directly to your public MCP URL."""
    answer, trace = ask_remote_with_trace(body.question)
    return AskResponse(
        answer=answer,
        trace_id=trace.trace_id if trace else None,
        duration_ms=trace.duration_ms if trace else None,
        tool_calls_count=len(trace.tool_calls) if trace else 0,
    )


# -------------------------------------------------------------
# Langfuse Monitoring & Dashboard APIs
# -------------------------------------------------------------

@router.get("/api/monitoring/stats")
def get_monitoring_stats() -> Dict[str, Any]:
    """Return aggregated metrics (total requests, tool breakdown, latency, tokens, Langfuse status)."""
    return monitoring_tracker.get_stats()


@router.get("/api/monitoring/traces")
def get_monitoring_traces(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    """Return list of traces with optional filtering by query or mode."""
    return monitoring_tracker.get_traces(limit=limit, offset=offset, search=search, mode=mode)


@router.get("/api/monitoring/traces/{trace_id}")
def get_trace_detail(trace_id: str) -> Dict[str, Any]:
    """Return detailed trace including prompt messages, tool spans, and token metrics."""
    trace = monitoring_tracker.get_trace_by_id(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace with ID '{trace_id}' not found.")
    return trace


@router.post("/api/monitoring/clear")
def clear_traces() -> Dict[str, bool]:
    """Clear local trace history."""
    monitoring_tracker.clear_traces()
    return {"cleared": True}


@router.get("/api/tools")
async def list_registered_tools() -> List[ToolInfo]:
    """Introspect and list all registered FastMCP tools and schemas."""
    async with Client(mcp) as client:
        tools = await client.list_tools()
        result = []
        for t in tools:
            schema = getattr(t, "input_schema", None) or getattr(t, "inputSchema", {})
            result.append(
                ToolInfo(
                    name=t.name,
                    description=t.description or "",
                    parameters=schema if isinstance(schema, dict) else {},
                )
            )
        return result


@router.get("/api/system/status")
def system_status() -> Dict[str, Any]:
    """Check configuration and connectivity for Groq, FastMCP, and Langfuse."""
    return {
        "groq": {
            "configured": config.is_groq_configured(),
            "model": config.GROQ_MODEL,
        },
        "mcp": {
            "mounted_path": "/mcp-server/mcp",
            "public_url": config.MCP_PUBLIC_URL or "Not set (needed for /ask/remote)",
            "public_url_valid": bool(
                config.MCP_PUBLIC_URL
                and config.MCP_PUBLIC_URL.startswith("https://")
                and "your-host.example.com" not in config.MCP_PUBLIC_URL
            ),
        },
        "langfuse": {
            "configured": config.is_langfuse_configured(),
            "host": config.LANGFUSE_HOST,
            "public_key_preview": (
                config.LANGFUSE_PUBLIC_KEY[:8] + "..." if config.LANGFUSE_PUBLIC_KEY else "Not configured"
            ),
        },
    }


@router.post("/api/demo/simulate")
async def simulate_demo_trace() -> Dict[str, Any]:
    """Simulate a sample agent workflow to showcase the Langfuse monitoring dashboard immediately."""
    trace = monitoring_tracker.start_trace(
        name="demo_agent_simulation",
        mode="local",
        question="What is 17 + 25, and what is the weather in Rajpura?",
    )

    # 1. First LLM step decides to call tools
    trace.log_llm_call(
        model=config.GROQ_MODEL,
        messages=[{"role": "user", "content": "What is 17 + 25, and what is the weather in Rajpura?"}],
        response_content="I'll calculate 17 + 25 and check the weather in Rajpura for you.",
        tool_calls=[
            {"id": "call_1", "function": {"name": "add", "arguments": '{"a": 17, "b": 25}'}, "type": "function"},
            {"id": "call_2", "function": {"name": "get_weather", "arguments": '{"city": "Rajpura"}'}, "type": "function"},
        ],
        usage={"prompt_tokens": 85, "completion_tokens": 42, "total_tokens": 127},
        duration_ms=310.5,
    )

    # 2. Tool executions
    async with Client(mcp) as client:
        res1 = await client.call_tool("add", {"a": 17, "b": 25})
        trace.log_tool_call(
            tool_name="add",
            arguments={"a": 17, "b": 25},
            result_text=res1.content[0].text,
            duration_ms=4.2,
        )

        res2 = await client.call_tool("get_weather", {"city": "Rajpura"})
        trace.log_tool_call(
            tool_name="get_weather",
            arguments={"city": "Rajpura"},
            result_text=res2.content[0].text,
            duration_ms=2.8,
        )

    # 3. Final synthesis
    final_output = f"17 + 25 equals {res1.content[0].text}. In Rajpura, {res2.content[0].text.lower()}"
    trace.log_llm_call(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "user", "content": "What is 17 + 25, and what is the weather in Rajpura?"},
            {"role": "assistant", "content": "I'll call add and get_weather."},
            {"role": "tool", "content": res1.content[0].text},
            {"role": "tool", "content": res2.content[0].text},
        ],
        response_content=final_output,
        usage={"prompt_tokens": 145, "completion_tokens": 28, "total_tokens": 173},
        duration_ms=280.0,
    )

    trace.finish(answer=final_output)
    return {
        "message": "Sample trace successfully simulated!",
        "trace": trace.to_dict(),
    }
