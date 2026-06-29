"""CLI entry point for mcp-probe.

Server commands are passed after a `--` separator, e.g.:
    mcp-probe inspect -- npx -y @modelcontextprotocol/server-everything
    mcp-probe inspect -- python my_server.py
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from .client import MCPClient, MCPError
from . import display as D


def _split_server_command(argv: list[str]) -> tuple[list[str], list[str]]:
    """Split argv into (cli_args, server_command) on the first `--`."""
    if "--" in argv:
        idx = argv.index("--")
        return argv[:idx], argv[idx + 1 :]
    return argv, []


def _open_client(server_cmd: list[str]) -> MCPClient:
    if not server_cmd:
        print(
            "Error: no server command provided. Use `--` followed by the command, e.g.\n"
            "  mcp-probe inspect -- npx -y @modelcontextprotocol/server-everything",
            file=sys.stderr,
        )
        sys.exit(2)
    client = MCPClient(server_cmd)
    try:
        client.connect()
    except MCPError as e:
        print(f"Failed to connect to MCP server: {e}", file=sys.stderr)
        client.close()
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: command not found: {server_cmd[0]!r}", file=sys.stderr)
        sys.exit(127)
    return client


def cmd_inspect(args) -> None:
    client = _open_client(args.server_cmd)
    try:
        print(D.server_card(client.server))

        tools, resources, prompts = [], [], []
        for label, fn, render in [
            ("Tools", client.list_tools, D.tool_entry),
            ("Resources", client.list_resources, D.resource_entry),
            ("Prompts", client.list_prompts, D.prompt_entry),
        ]:
            try:
                items = fn()
            except MCPError as e:
                print(f"\n{D.c(D.Color.BOLD, label)}: {D.c(D.Color.DIM, f'not supported ({e.message})')}")
                continue
            print(D.section(label, len(items)))
            if not items:
                print(D.c(D.Color.DIM, "  (empty)"))
            for i, item in enumerate(items):
                print(render(item, i) if render is D.tool_entry else render(item))
            # stash for summary
            if label == "Tools":
                tools = items
            elif label == "Resources":
                resources = items
            elif label == "Prompts":
                prompts = items

        total = len(tools) + len(resources) + len(prompts)
        print(f"\n{D.c(D.Color.GREEN + D.Color.BOLD, str(total))} capabilities discovered.")
    finally:
        client.close()


def cmd_tools(args) -> None:
    client = _open_client(args.server_cmd)
    try:
        try:
            tools = client.list_tools()
        except MCPError as e:
            print(f"Server does not support tools: {e.message}", file=sys.stderr)
            sys.exit(1)
        print(D.section("Tools", len(tools)))
        for i, tool in enumerate(tools):
            print(D.tool_entry(tool, i))
            if i < len(tools) - 1:
                print()
    finally:
        client.close()


def cmd_resources(args) -> None:
    client = _open_client(args.server_cmd)
    try:
        try:
            resources = client.list_resources()
        except MCPError as e:
            print(f"Server does not support resources: {e.message}", file=sys.stderr)
            sys.exit(1)
        print(D.section("Resources", len(resources)))
        for r in resources:
            print(D.resource_entry(r))
    finally:
        client.close()


def cmd_prompts(args) -> None:
    client = _open_client(args.server_cmd)
    try:
        try:
            prompts = client.list_prompts()
        except MCPError as e:
            print(f"Server does not support prompts: {e.message}", file=sys.stderr)
            sys.exit(1)
        print(D.section("Prompts", len(prompts)))
        for p in prompts:
            print(D.prompt_entry(p))
    finally:
        client.close()


def cmd_call(args) -> None:
    client = _open_client(args.server_cmd)
    try:
        arguments: dict = {}
        if args.args:
            try:
                arguments = json.loads(args.args)
            except json.JSONDecodeError as e:
                print(f"Error: --args must be valid JSON: {e}", file=sys.stderr)
                sys.exit(2)
            if not isinstance(arguments, dict):
                print("Error: --args must decode to a JSON object", file=sys.stderr)
                sys.exit(2)
        try:
            result = client.call_tool(args.tool, arguments)
        except MCPError as e:
            print(f"Tool call failed: {e}", file=sys.stderr)
            sys.exit(1)
        print(D.call_result(result))
    finally:
        client.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-probe",
        description="Probe and inspect any MCP (Model Context Protocol) server from the CLI.",
        epilog="Pass the server command after `--`, e.g.  mcp-probe inspect -- npx -y @pkg/server",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="Connect and show server info + all capabilities")
    p_inspect.set_defaults(func=cmd_inspect)

    p_tools = sub.add_parser("tools", help="List tools exposed by the server")
    p_tools.set_defaults(func=cmd_tools)

    p_resources = sub.add_parser("resources", help="List resources exposed by the server")
    p_resources.set_defaults(func=cmd_resources)

    p_prompts = sub.add_parser("prompts", help="List prompts exposed by the server")
    p_prompts.set_defaults(func=cmd_prompts)

    p_call = sub.add_parser("call", help="Invoke a tool on the server")
    p_call.add_argument("--tool", required=True, help="Tool name to invoke")
    p_call.add_argument("--args", help="Tool arguments as a JSON object string", default=None)
    p_call.set_defaults(func=cmd_call)

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    # On Windows the default stdout codec (e.g. GBK) can't encode the
    # box-drawing glyphs we use for display. Force UTF-8 with replacement
    # so the CLI never crashes on output encoding.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass

    argv = list(sys.argv[1:] if argv is None else argv)
    cli_args, server_cmd = _split_server_command(argv)

    parser = build_parser()
    args = parser.parse_args(cli_args)
    args.server_cmd = server_cmd
    args.func(args)


if __name__ == "__main__":
    main()
