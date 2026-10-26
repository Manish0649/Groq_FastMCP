from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastmcp.utilities.lifespan import combine_lifespans

from app.api.routes import router
from app.mcp_server.server import mcp


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    print("FastAPI starting with Groq + FastMCP...")
    yield
    print("FastAPI shutting down...")


# MCP endpoint lives at /mcp inside this sub-app
mcp_app = mcp.http_app()

app = FastAPI(
    title="Groq + FastMCP",
    description="Groq Cloud LLM agent integrated with FastMCP tool server and Langfuse observability.",
    version="1.0.0",
    lifespan=combine_lifespans(app_lifespan, mcp_app.lifespan),
)

# Include API routes
app.include_router(router)

# Mount the MCP server at /mcp-server -> final MCP endpoint: /mcp-server/mcp
app.mount("/mcp-server", mcp_app)
