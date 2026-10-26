"""Pydantic schemas for API requests, responses, and monitoring."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., description="User query or instruction for the agent")


class AskResponse(BaseModel):
    answer: str = Field(..., description="Final synthesized response from the agent")
    trace_id: Optional[str] = Field(None, description="Langfuse / Monitoring Trace ID")
    duration_ms: Optional[float] = Field(None, description="Total execution time in milliseconds")
    tool_calls_count: Optional[int] = Field(None, description="Number of tool calls executed")


class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class TraceSummary(BaseModel):
    trace_id: str
    name: str
    mode: str
    question: str
    output: Optional[str] = None
    status: str
    start_time: str
    duration_ms: float
    tokens: Dict[str, int]
    tool_calls_count: int
    langfuse_url: Optional[str] = None
    langfuse_synced: bool
