"""FastMCP instance and tool registration."""
from fastmcp import FastMCP
from app.mcp_server.tools.math_tools import add, multiply
from app.mcp_server.tools.weather_tools import get_weather

mcp = FastMCP("Tools")
mcp.tool(add)
mcp.tool(multiply)
mcp.tool(get_weather)
