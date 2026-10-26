"""Groq + FastMCP + Langfuse Observability & Agent Console in Streamlit."""
import os
import json
import asyncio
from datetime import datetime
import streamlit as st

# Configure Streamlit page layout and branding
st.set_page_config(
    page_title="Groq + FastMCP + Langfuse Hub",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for sleek dark theme and cards
st.markdown("""
<style>
    /* Metric Card styling */
    div[data-testid="stMetric"] {
        background: rgba(18, 27, 48, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
    }
    
    /* Code blocks */
    div[data-testid="stCodeBlock"] {
        border-radius: 8px;
    }
    
    /* Custom tag badges */
    .status-badge-success {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 999px;
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.35);
        font-size: 0.75rem;
        font-weight: 600;
    }
    .status-badge-error {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 999px;
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.35);
        font-size: 0.75rem;
        font-weight: 600;
    }
    .status-badge-info {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 999px;
        background: rgba(139, 92, 246, 0.15);
        color: #c084fc;
        border: 1px solid rgba(139, 92, 246, 0.35);
        font-size: 0.75rem;
        font-weight: 600;
    }
    .tool-pill {
        display: inline-block;
        padding: 2px 7px;
        margin: 2px;
        border-radius: 4px;
        background: rgba(249, 115, 22, 0.15);
        color: #fb923c;
        border: 1px solid rgba(249, 115, 22, 0.3);
        font-family: monospace;
        font-size: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

# Import backend modules
from app import config
from app.monitoring.tracker import monitoring_tracker
from app.llm.groq_local import ask_local_with_trace
from app.llm.groq_remote import ask_remote_with_trace
from app.mcp_server.server import mcp
from fastmcp import Client


# ---------------------------------------------------------------------------
# Sidebar: System Status & Navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚡ Groq + FastMCP")
    st.markdown("<p style='color: #8b5cf6; font-size: 0.85rem; font-weight: 600;'>LANGFUSE OBSERVABILITY HUB</p>", unsafe_allow_html=True)
    st.divider()

    menu = st.radio(
        "Navigation",
        ["💬 Agent Playground", "📊 Langfuse Monitoring", "🛠️ FastMCP Tools", "⚙️ Config & Architecture"],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("### System Health")

    # Groq Status
    groq_ok = config.is_groq_configured()
    if groq_ok:
        st.markdown(f"**Groq Cloud:** <span class='status-badge-success'>Connected</span>", unsafe_allow_html=True)
        st.caption(f"Model: `{config.GROQ_MODEL}`")
    else:
        st.markdown(f"**Groq Cloud:** <span class='status-badge-error'>Key Missing</span>", unsafe_allow_html=True)
        st.caption("Set `GROQ_API_KEY` in `.env`")

    # FastMCP Status
    st.markdown(f"**FastMCP Server:** <span class='status-badge-success'>Active</span>", unsafe_allow_html=True)
    st.caption("Mount: `/mcp-server/mcp`")

    # Langfuse Status
    lf_ok = config.is_langfuse_configured()
    if lf_ok:
        st.markdown(f"**Langfuse:** <span class='status-badge-success'>Cloud Synced</span>", unsafe_allow_html=True)
        st.caption(f"Host: `{config.LANGFUSE_HOST}`")
    else:
        st.markdown(f"**Langfuse:** <span class='status-badge-info'>Local Tracing</span>", unsafe_allow_html=True)
        st.caption("Tracking locally in-memory")

    st.divider()

    # Quick Demo Simulation Button
    if st.button("⚡ Run Demo Simulation Trace", use_container_width=True, help="Simulate a sample agent workflow calling add and get_weather tools"):
        with st.spinner("Generating demo agent trace with FastMCP tools..."):
            trace = monitoring_tracker.start_trace(
                name="demo_agent_simulation",
                mode="local",
                question="What is 17 + 25, and what is the weather in Rajpura?",
            )

            # LLM first step
            trace.log_llm_call(
                model=config.GROQ_MODEL,
                messages=[{"role": "user", "content": "What is 17 + 25, and what is the weather in Rajpura?"}],
                response_content="I'll calculate 17 + 25 and check the weather in Rajpura.",
                tool_calls=[
                    {"id": "call_1", "function": {"name": "add", "arguments": '{"a": 17, "b": 25}'}, "type": "function"},
                    {"id": "call_2", "function": {"name": "get_weather", "arguments": '{"city": "Rajpura"}'}, "type": "function"},
                ],
                usage={"prompt_tokens": 82, "completion_tokens": 40, "total_tokens": 122},
                duration_ms=290.0,
            )

            # In-memory tool execution
            async def run_demo_tools():
                async with Client(mcp) as client:
                    r1 = await client.call_tool("add", {"a": 17, "b": 25})
                    r2 = await client.call_tool("get_weather", {"city": "Rajpura"})
                    return r1.content[0].text, r2.content[0].text

            res_add, res_weather = asyncio.run(run_demo_tools())
            trace.log_tool_call(tool_name="add", arguments={"a": 17, "b": 25}, result_text=res_add, duration_ms=4.1)
            trace.log_tool_call(tool_name="get_weather", arguments={"city": "Rajpura"}, result_text=res_weather, duration_ms=3.2)

            final_output = f"17 + 25 = {res_add}. In Rajpura, {res_weather.lower()}"
            trace.log_llm_call(
                model=config.GROQ_MODEL,
                messages=[{"role": "user", "content": "What is 17 + 25, and what is the weather in Rajpura?"}, {"role": "assistant", "content": final_output}],
                response_content=final_output,
                usage={"prompt_tokens": 140, "completion_tokens": 26, "total_tokens": 166},
                duration_ms=260.0,
            )
            trace.finish(answer=final_output)
            st.success("Demo trace generated and recorded in Langfuse!")
            st.rerun()

    if st.button("🗑️ Clear Trace History", use_container_width=True):
        monitoring_tracker.clear_traces()
        st.info("Traces cleared.")
        st.rerun()


# ---------------------------------------------------------------------------
# TAB 1: Agent Playground
# ---------------------------------------------------------------------------
if menu == "💬 Agent Playground":
    st.title("💬 Agent Execution Console")
    st.markdown("Ask natural language queries that trigger registered **FastMCP math and weather tools**, observed via **Langfuse**.")

    col1, col2 = st.columns([1.2, 0.8])

    with col1:
        # Mode selector
        mode = st.radio(
            "Agent Mode:",
            ["Local Loop (/ask/local)", "Remote MCP (/ask/remote)"],
            horizontal=True,
            help="Local loop executes tool calls in Python. Remote MCP delegates tool execution to Groq Cloud servers via Responses API."
        )
        is_local = "Local" in mode

        if is_local:
            st.caption("💡 **Local Loop**: FastMCP Client runs in-memory. Groq Cloud coordinates tool calls.")
        else:
            st.caption(f"☁️ **Remote MCP**: Groq connects directly to public URL: `{config.MCP_PUBLIC_URL or 'Not configured'}`")

        # Preset buttons
        st.markdown("**Quick Presets:**")
        p_cols = st.columns(3)
        prompt_val = ""
        if p_cols[0].button("➕ Weather + Math"):
            st.session_state["user_prompt"] = "What is 17 + 25, and what is the weather in Rajpura?"
        if p_cols[1].button("🔢 Multi-step Math"):
            st.session_state["user_prompt"] = "Calculate 482 * 19 and add 350 to it."
        if p_cols[2].button("☀️ Weather Check"):
            st.session_state["user_prompt"] = "What is the weather in Tokyo and Paris?"

        default_prompt = st.session_state.get("user_prompt", "What is 17 + 25, and what is the weather in Rajpura?")
        user_question = st.text_area("Your Question / Prompt:", value=default_prompt, height=100)

        run_btn = st.button("🚀 Run Agent", type="primary", use_container_width=True)

    with col2:
        st.markdown("### Output & Trace Summary")
        output_placeholder = st.empty()

        if not run_btn and "last_result" not in st.session_state:
            output_placeholder.info("Enter a prompt and click **Run Agent** to execute.")

    # Execution handling
    if run_btn and user_question.strip():
        with st.spinner("Executing agent loop & recording Langfuse spans..."):
            if is_local:
                answer, trace = asyncio.run(ask_local_with_trace(user_question.strip()))
            else:
                answer, trace = ask_remote_with_trace(user_question.strip())

            st.session_state["last_result"] = {
                "answer": answer,
                "trace": trace.to_dict() if trace else None,
                "is_error": trace.status == "ERROR" if trace else False,
            }

    # Render last result if present
    if "last_result" in st.session_state:
        res = st.session_state["last_result"]
        trace = res["trace"]

        with col2:
            if res["is_error"]:
                output_placeholder.error(f"**Execution Error:**\n\n{res['answer']}")
            else:
                output_placeholder.success(f"**Synthesized Answer:**\n\n{res['answer']}")

            if trace:
                m1, m2, m3 = st.columns(3)
                m1.metric("Latency", f"{trace['duration_ms']} ms")
                m2.metric("Tools Used", trace["tool_calls_count"])
                m3.metric("Tokens", trace["tokens"]["total"])

                st.caption(f"**Trace ID:** `{trace['trace_id']}`")
                if trace.get("langfuse_url"):
                    st.markdown(f"[🔗 Open in Langfuse Dashboard]({trace['langfuse_url']})")

        # Step-by-step waterfall execution details
        if trace and trace.get("tool_calls"):
            st.divider()
            st.markdown("### 🔍 Step-by-Step Execution Trace")
            for idx, tc in enumerate(trace["tool_calls"]):
                with st.expander(f"🛠️ Tool Call #{idx + 1}: {tc['tool']} ({tc['duration_ms']} ms)", expanded=True):
                    c_in, c_out = st.columns(2)
                    with c_in:
                        st.markdown("**Arguments:**")
                        st.json(tc["arguments"])
                    with c_out:
                        st.markdown("**Tool Return Output:**")
                        st.code(tc["result"])


# ---------------------------------------------------------------------------
# TAB 2: Langfuse Monitoring Dashboard
# ---------------------------------------------------------------------------
elif menu == "📊 Langfuse Monitoring":
    st.title("📊 Langfuse LLM Observability & Tracing")
    st.markdown("Live monitoring metrics, token usage, tool invocation breakdown, and execution waterfall trees.")

    stats = monitoring_tracker.get_stats()

    # Top KPI Banner
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total Traces", stats["total_traces"], f"{stats['success_rate']}% success")
    kpi2.metric("FastMCP Tool Calls", stats["total_tool_calls"], ", ".join(stats["tool_usage_breakdown"].keys()) or "None")
    kpi3.metric("Avg Latency", f"{stats['avg_duration_ms']} ms")
    kpi4.metric("Total Tokens", stats["total_tokens"]["total"], f"P: {stats['total_tokens']['prompt']} | C: {stats['total_tokens']['completion']}")

    st.divider()

    # Filter Toolbar
    f_col1, f_col2, f_col3 = st.columns([1, 2, 1])
    with f_col1:
        mode_filter = st.selectbox("Filter Mode:", ["All", "local", "remote"])
    with f_col2:
        search_query = st.text_input("Search traces by prompt, tool, or ID:", placeholder="Type to search...")
    with f_col3:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

    # Retrieve filtered traces
    traces = monitoring_tracker.get_traces(
        limit=50,
        mode=mode_filter if mode_filter != "All" else None,
        search=search_query if search_query else None,
    )

    if not traces:
        st.info("No traces recorded yet. Use the **Agent Playground** or click **Run Demo Simulation Trace** in the sidebar.")
    else:
        st.markdown(f"### Recent Traces ({len(traces)})")

        # Table view
        table_data = []
        for t in traces:
            tools_str = ", ".join([tc["tool"] for tc in t["tool_calls"]]) or "—"
            table_data.append({
                "Status": t["status"],
                "Trace ID": t["trace_id"][:8] + "...",
                "Mode": t["mode"].upper(),
                "User Prompt": t["question"],
                "Tools Used": tools_str,
                "Latency": f"{t['duration_ms']} ms",
                "Tokens": t["tokens"]["total"],
                "Timestamp": t["start_time"][:19].replace("T", " "),
            })

        st.dataframe(table_data, use_container_width=True, hide_index=True)

        # Trace Detail Inspector
        st.divider()
        st.markdown("### 🔎 Trace Deep-Dive Inspector")

        trace_ids = [t["trace_id"] for t in traces]
        selected_id = st.selectbox("Select Trace to Inspect:", trace_ids, format_func=lambda tid: f"{tid} — {next((t['question'] for t in traces if t['trace_id'] == tid), '')[:50]}")

        sel_trace = next((t for t in traces if t["trace_id"] == selected_id), None)
        if sel_trace:
            st.markdown(f"#### Trace: `{sel_trace['name']}` ({sel_trace['trace_id']})")
            
            # QA Side-by-side
            qa1, qa2 = st.columns(2)
            with qa1:
                st.markdown("**User Question:**")
                st.info(sel_trace["question"])
            with qa2:
                st.markdown("**Agent Output:**")
                if sel_trace["status"] == "SUCCESS":
                    st.success(sel_trace["output"])
                else:
                    st.error(sel_trace.get("error") or "Execution failed")

            # Waterfall Spans Tree
            st.markdown("#### 🌊 Execution Waterfall Tree")
            
            with st.container():
                st.markdown(f"**Root Trace:** `{sel_trace['name']}` — `{sel_trace['duration_ms']} ms` (Mode: `{sel_trace['mode']}`)")

                # LLM generations
                if sel_trace.get("llm_calls"):
                    for idx, llm in enumerate(sel_trace["llm_calls"]):
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;⚡ **LLM Generation #{idx + 1}**: `{llm['model']}` — `{llm['duration_ms']} ms` ({llm['usage']['total_tokens']} tokens)")

                # Tool spans
                if sel_trace.get("tool_calls"):
                    for tc in sel_trace["tool_calls"]:
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🛠️ **MCP Tool**: `{tc['tool']}` — `{tc['duration_ms']} ms`")
                        with st.expander(f"View `{tc['tool']}` parameters and return output"):
                            st.write("**Input:**", tc["arguments"])
                            st.write("**Output:**", tc["result"])

            # Raw JSON viewer
            with st.expander("📄 View Raw Trace JSON Payload"):
                st.json(sel_trace)

            if sel_trace.get("langfuse_url"):
                st.link_button("🌐 Open in Langfuse Cloud Dashboard", sel_trace["langfuse_url"])


# ---------------------------------------------------------------------------
# TAB 3: MCP Tools Catalog
# ---------------------------------------------------------------------------
elif menu == "🛠️ FastMCP Tools":
    st.title("🛠️ Registered FastMCP Tools")
    st.markdown("Tools registered directly in FastMCP and exposed to Groq Cloud models.")

    async def get_tools_list():
        async with Client(mcp) as client:
            return await client.list_tools()

    tools = asyncio.run(get_tools_list())

    st.markdown(f"Found **{len(tools)}** active FastMCP tools registered in [`app/mcp_server/server.py`](file:///c:/Fellowship_projects/GROQ_FastMCP/app/mcp_server/server.py):")

    cols = st.columns(min(len(tools), 3))
    for idx, t in enumerate(tools):
        with cols[idx % len(cols)]:
            st.markdown(f"### `{t.name}`")
            st.write(t.description or "No description.")
            schema = getattr(t, "input_schema", None) or getattr(t, "inputSchema", {})
            st.markdown("**Parameters Schema:**")
            st.json(schema)


# ---------------------------------------------------------------------------
# TAB 4: Config & Architecture
# ---------------------------------------------------------------------------
elif menu == "⚙️ Config & Architecture":
    st.title("⚙️ Architecture & Configuration Guide")
    st.markdown("""
    ### System Architecture:
    1. **FastMCP Server**: Plain Python functions (`add`, `multiply`, `get_weather`) registered via `@mcp.tool`.
    2. **FastAPI Lifespan Integration**: Combines FastAPI lifespan with `mcp.http_app()` lifespan using `combine_lifespans`.
    3. **Groq Local Loop**: In-memory `Client(mcp)` converts tools to OpenAI format and loops chat completions.
    4. **Groq Remote MCP**: Groq Cloud servers connect directly to your public HTTPS MCP server via Responses API.
    5. **Langfuse Observability**: Captures agent traces, generations, tool calls, latencies, and token counts.
    """)

    st.markdown("### Environment Variables (`.env`)")
    st.code(f"""
GROQ_API_KEY={config.GROQ_API_KEY[:8] + '...' if config.GROQ_API_KEY else 'Not set'}
GROQ_MODEL={config.GROQ_MODEL}
MCP_PUBLIC_URL={config.MCP_PUBLIC_URL or 'Not set'}
LANGFUSE_PUBLIC_KEY={config.LANGFUSE_PUBLIC_KEY[:8] + '...' if config.LANGFUSE_PUBLIC_KEY else 'Not set'}
LANGFUSE_HOST={config.LANGFUSE_HOST}
    """, language="env")
