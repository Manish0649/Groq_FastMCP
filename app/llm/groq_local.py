"""Local Agent Loop with FastMCP Tools and Langfuse Monitoring."""
import json
import time
from typing import Any, Dict, List, Optional, Tuple
from fastmcp import Client
from groq import AsyncGroq
from app import config
from app.mcp_server.server import mcp
from app.monitoring.tracker import monitoring_tracker


def get_groq_client() -> AsyncGroq:
    """Instantiate AsyncGroq with API key."""
    api_key = config.GROQ_API_KEY or "dummy_key_for_init"
    return AsyncGroq(api_key=api_key)


async def ask_local_with_trace(question: str) -> Tuple[str, Any]:
    """Execute the local agent loop and record comprehensive Langfuse traces."""
    trace = monitoring_tracker.start_trace(
        name="groq_fastmcp_ask_local",
        mode="local",
        question=question,
    )

    if not config.is_groq_configured():
        msg = (
            "GROQ_API_KEY is not set. Please set a valid GROQ_API_KEY in your .env file. "
            "Get a free API key at https://console.groq.com/keys."
        )
        trace.finish(error=msg)
        return msg, trace

    groq = get_groq_client()

    try:
        # In-memory FastMCP Client transport
        async with Client(mcp) as mcp_client:
            mcp_tools = await mcp_client.list_tools()
            tools: List[Dict[str, Any]] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": getattr(t, "input_schema", None) or getattr(t, "inputSchema", {}),
                    },
                }
                for t in mcp_tools
            ]

            messages: List[Dict[str, Any]] = [{"role": "user", "content": question}]

            max_iterations = 10
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                t_start = time.time()
                resp = await groq.chat.completions.create(
                    model=config.GROQ_MODEL,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
                t_duration = (time.time() - t_start) * 1000

                choice = resp.choices[0]
                msg = choice.message
                raw_tool_calls = [
                    {
                        "id": c.id,
                        "function": {"name": c.function.name, "arguments": c.function.arguments},
                        "type": c.type,
                    }
                    for c in (msg.tool_calls or [])
                ]

                # Extract usage tokens if available
                usage = None
                if getattr(resp, "usage", None):
                    usage = {
                        "prompt_tokens": resp.usage.prompt_tokens,
                        "completion_tokens": resp.usage.completion_tokens,
                        "total_tokens": resp.usage.total_tokens,
                    }

                # Log LLM generation to Langfuse trace
                trace.log_llm_call(
                    model=config.GROQ_MODEL,
                    messages=list(messages),
                    response_content=msg.content,
                    tool_calls=raw_tool_calls,
                    usage=usage,
                    duration_ms=t_duration,
                )

                messages.append(msg)

                # If no tool calls, synthesis is complete
                if not msg.tool_calls:
                    final_answer = msg.content or ""
                    trace.finish(answer=final_answer)
                    return final_answer, trace

                # Execute requested FastMCP tools
                for call in msg.tool_calls:
                    tool_start = time.time()
                    try:
                        args = json.loads(call.function.arguments or "{}")
                    except Exception as json_err:
                        args = {}

                    try:
                        result = await mcp_client.call_tool(call.function.name, args)
                        result_text = result.content[0].text if result.content else str(result)
                        tool_duration = (time.time() - tool_start) * 1000
                        trace.log_tool_call(
                            tool_name=call.function.name,
                            arguments=args,
                            result_text=result_text,
                            duration_ms=tool_duration,
                            is_error=False,
                        )
                    except Exception as tool_err:
                        result_text = f"Tool Error: {str(tool_err)}"
                        tool_duration = (time.time() - tool_start) * 1000
                        trace.log_tool_call(
                            tool_name=call.function.name,
                            arguments=args,
                            result_text=result_text,
                            duration_ms=tool_duration,
                            is_error=True,
                        )

                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result_text,
                    })

            final_answer = msg.content or "Completed tool execution."
            trace.finish(answer=final_answer)
            return final_answer, trace

    except Exception as e:
        error_msg = f"Local agent error: {str(e)}"
        trace.finish(error=error_msg)
        return error_msg, trace


async def ask_local(question: str) -> str:
    """Standard signature as specified in project documentation."""
    answer, _ = await ask_local_with_trace(question)
    return answer
