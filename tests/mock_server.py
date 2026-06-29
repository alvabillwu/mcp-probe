"""A tiny mock MCP server for testing mcp-probe.

Speaks JSON-RPC 2.0 over newline-delimited stdio. Exposes one tool
(`echo`), one resource, and one prompt.
"""

import json
import sys


def main() -> None:
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = msg.get("method")
        msg_id = msg.get("id")
        resp: dict = {}

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                    "serverInfo": {"name": "mock-mcp", "version": "1.0.0"},
                },
            }
        elif method == "notifications/initialized":
            continue  # notification — no response
        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": "echo",
                            "description": "Echo back the provided text",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"text": {"type": "string"}},
                                "required": ["text"],
                            },
                        }
                    ]
                },
            }
        elif method == "tools/call":
            name = msg.get("params", {}).get("name")
            if name != "echo":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": f"Unknown tool: {name}"},
                }
            else:
                args = msg.get("params", {}).get("arguments", {})
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": args.get("text", "")}],
                        "isError": False,
                    },
                }
        elif method == "resources/list":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "resources": [
                        {
                            "uri": "file://example.txt",
                            "name": "example",
                            "description": "An example resource",
                        }
                    ]
                },
            }
        elif method == "prompts/list":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "prompts": [
                        {"name": "greet", "description": "A greeting prompt", "arguments": []}
                    ]
                },
            }
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
