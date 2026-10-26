"""Langfuse Observability & Tracing Tracker for Groq + FastMCP.

Provides seamless instrumentation for both local agent loops and remote MCP calls.
Captures:
- Agent queries and responses
- LLM prompt messages, completions, latency, and token usage
- FastMCP tool executions, inputs, and outputs
- Live aggregated metrics and trace history for the frontend monitoring UI
- Automatic sync with Langfuse Cloud / Self-hosted when configured
"""
import os
import time
import uuid
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from app import config

logger = logging.getLogger("groq_fastmcp.monitoring")


class TraceSession:
    """Represents an active or completed trace for an agent request."""

    def __init__(self, trace_id: str, name: str, mode: str, question: str, langfuse_client: Optional[Any] = None):
        self.trace_id = trace_id
        self.name = name
        self.mode = mode  # 'local' or 'remote'
        self.question = question
        self.start_time = time.time()
        self.start_iso = datetime.now(timezone.utc).isoformat()
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0
        self.status = "RUNNING"
        self.output: Optional[str] = None
        self.error: Optional[str] = None

        self.llm_calls: List[Dict[str, Any]] = []
        self.tool_calls: List[Dict[str, Any]] = []
        self.tokens = {"prompt": 0, "completion": 0, "total": 0}

        self.langfuse_client = langfuse_client
        self.langfuse_observation = None
        self.langfuse_url: Optional[str] = None

        # Initialize Langfuse root observation if available
        if self.langfuse_client and config.is_langfuse_configured():
            try:
                self.langfuse_observation = self.langfuse_client.start_observation(
                    name=name,
                    as_type="agent",
                    input={"question": question, "mode": mode},
                    metadata={"mode": mode, "model": config.GROQ_MODEL},
                )
                host = config.LANGFUSE_HOST.rstrip("/")
                self.langfuse_url = f"{host}/project/traces/{self.trace_id}"
            except Exception as e:
                logger.warning(f"Failed to start Langfuse observation: {e}")

    def log_llm_call(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        response_content: Optional[str],
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        usage: Optional[Dict[str, int]] = None,
        duration_ms: float = 0.0,
    ) -> None:
        """Record an LLM chat completion step."""
        usage_data = usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        total_tokens = usage_data.get("total_tokens", prompt_tokens + completion_tokens)

        self.tokens["prompt"] += prompt_tokens
        self.tokens["completion"] += completion_tokens
        self.tokens["total"] += total_tokens

        record = {
            "id": f"llm_{len(self.llm_calls) + 1}",
            "model": model,
            "messages": messages,
            "response": response_content,
            "tool_calls": tool_calls or [],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "duration_ms": round(duration_ms, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.llm_calls.append(record)

        # Sync with Langfuse as a generation observation
        if self.langfuse_observation and config.is_langfuse_configured():
            try:
                out_content = response_content or (f"Tool calls: {json.dumps(tool_calls)}" if tool_calls else "")
                generation = self.langfuse_observation.start_observation(
                    name=f"groq_completion_{len(self.llm_calls)}",
                    as_type="generation",
                    model=model,
                    input=messages,
                    output=out_content,
                    usage_details={"input": prompt_tokens, "output": completion_tokens, "total": total_tokens},
                )
                generation.update(output=out_content)
                generation.end()
            except Exception as e:
                logger.warning(f"Failed to log Langfuse generation: {e}")

    def log_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result_text: str,
        duration_ms: float = 0.0,
        is_error: bool = False,
    ) -> None:
        """Record an MCP tool execution step."""
        record = {
            "id": f"tool_{len(self.tool_calls) + 1}",
            "tool": tool_name,
            "arguments": arguments,
            "result": result_text,
            "duration_ms": round(duration_ms, 2),
            "is_error": is_error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.tool_calls.append(record)

        # Sync with Langfuse as a tool observation
        if self.langfuse_observation and config.is_langfuse_configured():
            try:
                tool_obs = self.langfuse_observation.start_observation(
                    name=f"fastmcp_tool:{tool_name}",
                    as_type="tool",
                    input=arguments,
                    output=result_text,
                    level="ERROR" if is_error else "DEFAULT",
                )
                tool_obs.update(output=result_text)
                tool_obs.end()
            except Exception as e:
                logger.warning(f"Failed to log Langfuse tool observation: {e}")

    def finish(self, answer: Optional[str] = None, error: Optional[str] = None) -> None:
        """Complete the trace session."""
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        if error:
            self.status = "ERROR"
            self.error = error
        else:
            self.status = "SUCCESS"
            self.output = answer

        # Close Langfuse observation
        if self.langfuse_observation and config.is_langfuse_configured():
            try:
                self.langfuse_observation.update(
                    output=answer if not error else f"Error: {error}",
                    level="ERROR" if error else "DEFAULT",
                    status_message=error,
                )
                self.langfuse_observation.end()
                if self.langfuse_client:
                    self.langfuse_client.flush()
            except Exception as e:
                logger.warning(f"Failed to finish Langfuse observation: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to comprehensive JSON-serializable dictionary."""
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "mode": self.mode,
            "question": self.question,
            "output": self.output,
            "status": self.status,
            "error": self.error,
            "start_time": self.start_iso,
            "duration_ms": self.duration_ms,
            "tokens": self.tokens,
            "llm_calls_count": len(self.llm_calls),
            "tool_calls_count": len(self.tool_calls),
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "langfuse_url": self.langfuse_url,
            "langfuse_synced": bool(self.langfuse_observation is not None and config.is_langfuse_configured()),
        }


class MonitoringTracker:
    """Central singleton managing all monitoring, traces, and metrics."""

    def __init__(self):
        self.traces: List[TraceSession] = []
        self.max_traces = 500
        self.langfuse_client: Optional[Any] = None
        self._init_langfuse()

    def _init_langfuse(self) -> None:
        """Initialize Langfuse client if credentials are configured."""
        if config.is_langfuse_configured():
            try:
                from langfuse import Langfuse
                self.langfuse_client = Langfuse(
                    public_key=config.LANGFUSE_PUBLIC_KEY,
                    secret_key=config.LANGFUSE_SECRET_KEY,
                    host=config.LANGFUSE_HOST,
                )
                logger.info(f"Langfuse initialized successfully with host: {config.LANGFUSE_HOST}")
            except Exception as e:
                logger.warning(f"Langfuse initialization error: {e}")
                self.langfuse_client = None
        else:
            self.langfuse_client = None

    def start_trace(self, name: str, mode: str, question: str) -> TraceSession:
        """Start a new agent execution trace."""
        trace_id = str(uuid.uuid4())
        session = TraceSession(
            trace_id=trace_id,
            name=name,
            mode=mode,
            question=question,
            langfuse_client=self.langfuse_client,
        )
        self.traces.insert(0, session)
        if len(self.traces) > self.max_traces:
            self.traces.pop()
        return session

    def get_traces(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent traces with optional filtering."""
        filtered = self.traces
        if mode and mode != "all":
            filtered = [t for t in filtered if t.mode.lower() == mode.lower()]
        if search:
            query = search.lower()
            filtered = [
                t for t in filtered
                if query in t.question.lower()
                or (t.output and query in t.output.lower())
                or t.trace_id.lower().startswith(query)
                or any(query in tc["tool"].lower() for tc in t.tool_calls)
            ]
        return [t.to_dict() for t in filtered[offset : offset + limit]]

    def get_trace_by_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific trace by ID."""
        for t in self.traces:
            if t.trace_id == trace_id:
                return t.to_dict()
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Aggregate real-time metrics across all traces."""
        total_traces = len(self.traces)
        if total_traces == 0:
            return {
                "total_traces": 0,
                "successful_traces": 0,
                "error_traces": 0,
                "success_rate": 100.0,
                "total_tool_calls": 0,
                "avg_duration_ms": 0.0,
                "total_tokens": {"prompt": 0, "completion": 0, "total": 0},
                "tool_usage_breakdown": {},
                "mode_breakdown": {"local": 0, "remote": 0},
                "langfuse_configured": config.is_langfuse_configured(),
                "langfuse_host": config.LANGFUSE_HOST,
                "groq_configured": config.is_groq_configured(),
                "groq_model": config.GROQ_MODEL,
            }

        successful = sum(1 for t in self.traces if t.status == "SUCCESS")
        errors = sum(1 for t in self.traces if t.status == "ERROR")
        total_duration = sum(t.duration_ms for t in self.traces)
        total_tools = sum(len(t.tool_calls) for t in self.traces)

        tool_counts: Dict[str, int] = {}
        for t in self.traces:
            for tc in t.tool_calls:
                name = tc.get("tool", "unknown")
                tool_counts[name] = tool_counts.get(name, 0) + 1

        prompt_tokens = sum(t.tokens["prompt"] for t in self.traces)
        comp_tokens = sum(t.tokens["completion"] for t in self.traces)
        tot_tokens = sum(t.tokens["total"] for t in self.traces)

        local_count = sum(1 for t in self.traces if t.mode == "local")
        remote_count = sum(1 for t in self.traces if t.mode == "remote")

        return {
            "total_traces": total_traces,
            "successful_traces": successful,
            "error_traces": errors,
            "success_rate": round((successful / total_traces) * 100, 1) if total_traces > 0 else 100.0,
            "total_tool_calls": total_tools,
            "avg_duration_ms": round(total_duration / total_traces, 1) if total_traces > 0 else 0.0,
            "total_tokens": {
                "prompt": prompt_tokens,
                "completion": comp_tokens,
                "total": tot_tokens,
            },
            "tool_usage_breakdown": tool_counts,
            "mode_breakdown": {"local": local_count, "remote": remote_count},
            "langfuse_configured": config.is_langfuse_configured(),
            "langfuse_host": config.LANGFUSE_HOST,
            "groq_configured": config.is_groq_configured(),
            "groq_model": config.GROQ_MODEL,
        }

    def clear_traces(self) -> None:
        """Clear trace history for fresh testing."""
        self.traces.clear()


monitoring_tracker = MonitoringTracker()
