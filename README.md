# 🔌 mcp-probe

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![No Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)](#)

**Probe and inspect any [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server from the CLI.**

`mcp-probe` is a zero-dependency MCP client that speaks JSON-RPC 2.0 over stdio. Connect to any MCP server, discover its tools, resources, and prompts, and invoke tools — all from your terminal. Great for debugging servers you're building, auditing third-party servers, or scripting MCP interactions.

## Features

- 🔍 **Discover** — list tools, resources, and prompts exposed by any MCP server
- 🛠️ **Invoke** — call tools with JSON arguments and pretty-print results
- 🚫 **Zero dependencies** — pure Python stdlib, implements the MCP protocol directly
- 🎨 **Readable output** — color-coded, structured terminal display
- 🔧 **Any server** — works with any stdio MCP server (`npx`, `python`, `node`, …)

## Quick Start

```bash
pip install mcp-probe
```

## Usage

> Pass the server command after `--`. `mcp-probe` spawns it as a subprocess and speaks MCP over stdio.

### Inspect a server (everything at once)
```bash
mcp-probe inspect -- npx -y @modelcontextprotocol/server-everything
```

```
● MCP Server
  name:     Everything
  version:  1.0.0
  protocol: 2024-11-05
  caps:     tools, resources, prompts

Tools (1)
  ▸ echo — Echoes back the input
      params: message*:string
...
```

### List only tools
```bash
mcp-probe tools -- npx -y @modelcontextprotocol/server-everything
```

### List resources / prompts
```bash
mcp-probe resources -- python my_server.py
mcp-probe prompts -- python my_server.py
```

### Invoke a tool
```bash
mcp-probe call --tool echo --args '{"message":"hello"}' -- npx -y @modelcontextprotocol/server-everything
```

```
✓ Result
hello
```

## How It Works

`mcp-probe` implements the MCP [stdio transport](https://modelcontextprotocol.io/docs/concepts/transports):

1. Spawns your server command as a subprocess
2. Sends the `initialize` JSON-RPC request and reads the server's capabilities
3. Sends the `notifications/initialized` acknowledgment
4. Calls `tools/list`, `resources/list`, `prompts/list`, and `tools/call` as requested
5. Renders results and tears down the subprocess

Messages are newline-delimited JSON (JSON-RPC 2.0). No SDK required.

## Development

```bash
git clone https://github.com/alvabillwu/mcp-probe.git
cd mcp-probe
pip install -e ".[dev]"
pytest -v
```

The test suite runs against an in-repo mock MCP server (`tests/mock_server.py`), so it's fully self-contained.

## License

MIT © [alvabillwu](https://github.com/alvabillwu)
