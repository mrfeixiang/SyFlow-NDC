#!/usr/bin/env python3
"""Generate MCP server configuration for SyFlow NDC platform.

Creates mcp_config.json with paths to the provenance MCP server.
Uses the current Python interpreter path for portability.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MCP_DIR = PROJECT_ROOT / "src" / "mcp_servers"


def generate_mcp_config(output_path: Path | None = None) -> dict:
    """Generate MCP server configuration."""
    python = sys.executable

    config = {
        "mcpServers": {
            "provenance": {
                "command": python,
                "args": [str(MCP_DIR / "provenance_mcp" / "server.py")],
                "env": {
                    "SYFLOW_RUNS_DIR": str(PROJECT_ROOT / "runs"),
                },
            },
        },
    }

    out = output_path or PROJECT_ROOT / "mcp_config.json"
    with open(out, "w") as f:
        json.dump(config, f, indent=2)

    print(f"MCP config written to: {out}")
    print(f"Python interpreter: {python}")
    print(f"Servers configured: {list(config['mcpServers'].keys())}")

    return config


if __name__ == "__main__":
    generate_mcp_config()
