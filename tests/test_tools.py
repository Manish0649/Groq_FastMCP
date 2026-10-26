import pytest
from fastmcp import Client
from app.mcp_server.server import mcp


@pytest.mark.asyncio
async def test_add():
    async with Client(mcp) as c:
        result = await c.call_tool("add", {"a": 2, "b": 3})
        assert result.content[0].text == "5"


@pytest.mark.asyncio
async def test_multiply():
    async with Client(mcp) as c:
        result = await c.call_tool("multiply", {"a": 6, "b": 7})
        assert result.content[0].text == "42"


@pytest.mark.asyncio
async def test_weather():
    async with Client(mcp) as c:
        result = await c.call_tool("get_weather", {"city": "Rajpura"})
        assert "Rajpura" in result.content[0].text
        assert "28°C" in result.content[0].text


@pytest.mark.asyncio
async def test_tools_listed():
    async with Client(mcp) as c:
        names = {t.name for t in await c.list_tools()}
        assert {"add", "get_weather"} <= names
