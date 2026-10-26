import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"ok": True}


def test_system_status():
    res = client.get("/api/system/status")
    assert res.status_code == 200
    data = res.json()
    assert "groq" in data
    assert "mcp" in data
    assert "langfuse" in data


def test_tools_listing():
    res = client.get("/api/tools")
    assert res.status_code == 200
    tools = res.json()
    tool_names = {t["name"] for t in tools}
    assert {"add", "multiply", "get_weather"} <= tool_names


def test_monitoring_simulation_and_traces():
    # Simulate a demo trace
    sim_res = client.post("/api/demo/simulate")
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert "trace" in sim_data
    trace_id = sim_data["trace"]["trace_id"]

    # Verify trace appears in list
    traces_res = client.get("/api/monitoring/traces")
    assert traces_res.status_code == 200
    traces = traces_res.json()
    assert len(traces) >= 1
    assert any(t["trace_id"] == trace_id for t in traces)

    # Verify single trace retrieval
    detail_res = client.get(f"/api/monitoring/traces/{trace_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["trace_id"] == trace_id
    assert detail["status"] == "SUCCESS"
    assert len(detail["tool_calls"]) == 2

    # Verify stats
    stats_res = client.get("/api/monitoring/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_traces"] >= 1
    assert stats["total_tool_calls"] >= 2
