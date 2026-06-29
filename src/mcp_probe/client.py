"""Minimal MCP (Model Context Protocol) stdio client.

Implements JSON-RPC 2.0 over the newline-delimited stdio transport —
just enough to initialize a server and inspect its tools, resources,
and prompts, and to invoke tools. No external dependencies.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Optional

# Protocol version we advertise. Servers negotiate their own.
PROTOCOL_VERSION = "2024-11-05"


class MCPError(Exception):
    """Raised when the server returns a JSON-RPC error or drops the connection."""

    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.data = data


@dataclass
class ServerInfo:
    name: str
    version: str
    protocol_version: str
    capabilities: dict = field(default_factory=dict)


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict

    @classmethod
    def from_dict(cls, d: dict) -> "Tool":
        return cls(
            name=d.get("name", ""),
            description=d.get("description", ""),
            input_schema=d.get("inputSchema", {}) or {},
        )


@dataclass
class Resource:
    uri: str
    name: str
    description: str
    mime_type: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Resource":
        return cls(
            uri=d.get("uri", ""),
            name=d.get("name", ""),
            description=d.get("description", ""),
            mime_type=d.get("mimeType", ""),
        )


@dataclass
class Prompt:
    name: str
    description: str
    arguments: list

    @classmethod
    def from_dict(cls, d: dict) -> "Prompt":
        return cls(
            name=d.get("name", ""),
            description=d.get("description", ""),
            arguments=d.get("arguments", []) or [],
        )


class MCPClient:
    """Synchronous MCP client over the stdio transport."""

    def __init__(
        self,
        command: list[str],
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
    ):
        self.command = command
        self.cwd = cwd
        self.env = env
        self._proc: Optional[subprocess.Popen] = None
        self._next_id = 1
        self.server: Optional[ServerInfo] = None

    def __enter__(self) -> "MCPClient":
        self.connect()
        return self

    def __exit__(self, *exc) -> bool:
        self.close()
        return False

    def connect(self) -> ServerInfo:
        """Spawn the server and perform the initialize handshake."""
        full_env = None
        if self.env:
            full_env = {**os.environ, **self.env}

        self._proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.cwd,
            env=full_env,
            text=True,
            bufsize=1,  # line buffered
        )

        result = self._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "mcp-probe", "version": "0.1.0"},
            },
        )
        info = result.get("serverInfo", {})
        self.server = ServerInfo(
            name=info.get("name", "unknown"),
            version=info.get("version", "0.0.0"),
            protocol_version=result.get("protocolVersion", PROTOCOL_VERSION),
            capabilities=result.get("capabilities", {}) or {},
        )
        # Acknowledge initialization — required before most servers respond.
        self._notify("notifications/initialized", {})
        return self.server

    def close(self) -> None:
        """Tear down the server subprocess."""
        if self._proc is None:
            return
        try:
            if self._proc.stdin and not self._proc.stdin.closed:
                self._proc.stdin.close()
        except Exception:
            pass
        try:
            self._proc.terminate()
            self._proc.wait(timeout=3)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass
        self._proc = None

    # ── transport primitives ──────────────────────────────────────────

    def _send(self, payload: dict) -> None:
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(json.dumps(payload) + "\n")
        self._proc.stdin.flush()

    def _read(self) -> dict:
        assert self._proc and self._proc.stdout
        line = self._proc.stdout.readline()
        if not line:
            stderr = ""
            try:
                stderr = self._proc.stderr.read() if self._proc.stderr else ""
            except Exception:
                pass
            tail = f" (server stderr: {stderr.strip()[:500]})" if stderr else ""
            raise MCPError(-1, "Server closed connection" + tail)
        return json.loads(line)

    def _request(self, method: str, params: Optional[dict] = None) -> dict:
        msg_id = self._next_id
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}})
        # Skip server-initiated notifications until we see our response.
        while True:
            resp = self._read()
            if resp.get("id") == msg_id:
                if "error" in resp:
                    err = resp["error"]
                    raise MCPError(
                        err.get("code", -1),
                        err.get("message", "Unknown error"),
                        err.get("data"),
                    )
                return resp.get("result", {}) or {}
            # unrelated notification — ignore

    def _notify(self, method: str, params: Optional[dict] = None) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    # ── high-level operations ─────────────────────────────────────────

    def list_tools(self) -> list[Tool]:
        result = self._request("tools/list", {})
        return [Tool.from_dict(t) for t in result.get("tools", [])]

    def list_resources(self) -> list[Resource]:
        result = self._request("resources/list", {})
        return [Resource.from_dict(r) for r in result.get("resources", [])]

    def list_prompts(self) -> list[Prompt]:
        result = self._request("prompts/list", {})
        return [Prompt.from_dict(p) for p in result.get("prompts", [])]

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> dict:
        return self._request("tools/call", {"name": name, "arguments": arguments or {}})
