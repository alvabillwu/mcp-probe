"""Terminal display helpers for mcp-probe."""

import json
import sys


class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"


def _supports_color() -> bool:
    return getattr(sys.stdout, "isatty", lambda: False)()


def c(color: str, text: str) -> str:
    return f"{color}{text}{Color.RESET}" if _supports_color() else text


def server_card(server) -> str:
    lines = [
        c(Color.BOLD + Color.CYAN, "● MCP Server"),
        f"  {c(Color.DIM, 'name:')}     {server.name}",
        f"  {c(Color.DIM, 'version:')}  {server.version}",
        f"  {c(Color.DIM, 'protocol:')} {server.protocol_version}",
    ]
    caps = ", ".join(server.capabilities.keys()) or c(Color.DIM, "(none)")
    lines.append(f"  {c(Color.DIM, 'caps:')}      {caps}")
    return "\n".join(lines)


def tool_entry(tool, index: int) -> str:
    head = f"  {c(Color.GREEN, '▸')} {c(Color.BOLD, tool.name)}"
    if tool.description:
        head += c(Color.DIM, f" — {tool.description}")
    schema = tool.input_schema
    props = schema.get("properties", {}) if isinstance(schema, dict) else {}
    required = set(schema.get("required", []) if isinstance(schema, dict) else [])
    if props:
        param_strs = []
        for pname, pschema in props.items():
            ptype = pschema.get("type", "any") if isinstance(pschema, dict) else "any"
            mark = c(Color.RED, "*") if pname in required else ""
            param_strs.append(f"{pname}{mark}:{ptype}")
        head += "\n" + c(Color.DIM, "      params: ") + ", ".join(param_strs)
    return head


def resource_entry(resource) -> str:
    line = f"  {c(Color.BLUE, '▸')} {c(Color.BOLD, resource.name)}"
    if resource.uri:
        line += c(Color.DIM, f"  ({resource.uri})")
    if resource.description:
        line += "\n" + c(Color.DIM, f"      {resource.description}")
    return line


def prompt_entry(prompt) -> str:
    line = f"  {c(Color.MAGENTA, '▸')} {c(Color.BOLD, prompt.name)}"
    if prompt.description:
        line += c(Color.DIM, f" — {prompt.description}")
    if prompt.arguments:
        args = ", ".join(a.get("name", "?") for a in prompt.arguments)
        line += "\n" + c(Color.DIM, f"      args: {args}")
    return line


def call_result(result: dict) -> str:
    """Render a tools/call result."""
    if result.get("isError"):
        out = [c(Color.RED + Color.BOLD, "✗ Tool returned an error")]
    else:
        out = [c(Color.GREEN + Color.BOLD, "✓ Result")]
    for block in result.get("content", []):
        btype = block.get("type", "text")
        if btype == "text":
            out.append(block.get("text", ""))
        else:
            out.append(json.dumps(block, indent=2))
    return "\n".join(out)


def section(title: str, count: int) -> str:
    label = f"{title} ({count})" if count else f"{title} (0)"
    return f"\n{c(Color.BOLD, label)}"
