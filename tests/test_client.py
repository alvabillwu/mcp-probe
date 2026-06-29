"""Integration tests for mcp_probe.client against a mock MCP server."""

import sys
from pathlib import Path

import pytest

from mcp_probe.client import MCPClient, MCPError

MOCK_SERVER = str(Path(__file__).parent / "mock_server.py")


def make_client() -> MCPClient:
    return MCPClient([sys.executable, MOCK_SERVER])


def test_initialize_handshake():
    with make_client() as c:
        assert c.server is not None
        assert c.server.name == "mock-mcp"
        assert c.server.version == "1.0.0"
        assert c.server.protocol_version == "2024-11-05"
        assert "tools" in c.server.capabilities


def test_list_tools():
    with make_client() as c:
        tools = c.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "echo"
        assert "text" in tools[0].input_schema["properties"]
        assert "text" in tools[0].input_schema["required"]


def test_list_resources():
    with make_client() as c:
        resources = c.list_resources()
        assert len(resources) == 1
        assert resources[0].uri == "file://example.txt"
        assert resources[0].name == "example"


def test_list_prompts():
    with make_client() as c:
        prompts = c.list_prompts()
        assert len(prompts) == 1
        assert prompts[0].name == "greet"


def test_call_tool():
    with make_client() as c:
        result = c.call_tool("echo", {"text": "hello world"})
        assert result["isError"] is False
        assert result["content"][0]["text"] == "hello world"


def test_call_unknown_tool_raises():
    with make_client() as c:
        with pytest.raises(MCPError):
            c.call_tool("nonexistent", {})


def test_context_manager_closes_process():
    client = make_client()
    with client as c:
        c.list_tools()
        assert c._proc is not None
    assert client._proc is None


def test_multiple_requests_in_sequence():
    with make_client() as c:
        # id counter should increment correctly across requests
        tools = c.list_tools()
        resources = c.list_resources()
        prompts = c.list_prompts()
        result = c.call_tool("echo", {"text": "ok"})
        assert len(tools) == 1
        assert len(resources) == 1
        assert len(prompts) == 1
        assert result["content"][0]["text"] == "ok"
