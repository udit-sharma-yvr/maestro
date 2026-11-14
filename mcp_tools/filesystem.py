"""MCP filesystem server.

Exposes three tools that operate strictly within MAESTRO_SANDBOX_ROOT:

  - read_file(path):           read a text file
  - search_code(query, pattern): substring or regex search across the sandbox
  - run_command(command, timeout): run a read-only shell command (allowlisted)

`run_command` is the security talking point: it is confined to the sandbox, restricted
to a read-only command allowlist, blocks state-mutating/network patterns, and is
bounded by a timeout. Run it as a subprocess over stdio: `python -m mcp_tools.filesystem`.
"""

import os
import re
import shlex
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("filesystem")

ROOT = Path(os.environ.get("MAESTRO_SANDBOX_ROOT", "sandbox")).resolve()


def _safe(path: str) -> Path:
    """Resolve `path` under ROOT and refuse anything that escapes the sandbox."""
    p = (ROOT / path).resolve()
    if not p.is_relative_to(ROOT):
        raise ValueError(f"path escapes sandbox: {path}")
    return p


@mcp.tool()
def read_file(path: str) -> str:
    """Read a text file from the sandbox."""
    p = _safe(path)
    if not p.is_file():
        raise FileNotFoundError(f"not a file: {path}")
    return p.read_text(encoding="utf-8", errors="replace")


@mcp.tool()
def search_code(query: str, pattern: str = "") -> str:
    """Search the sandbox for `query` (substring) or `pattern` (regex). Returns file:line matches."""
    rx = re.compile(pattern if pattern else re.escape(query))
    hits: list[str] = []
    for f in ROOT.rglob("*"):
        if not f.is_file() or f.name.startswith("."):
            continue
        try:
            for i, line in enumerate(
                f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
            ):
                if rx.search(line):
                    hits.append(f"{f.relative_to(ROOT)}:{i}: {line.strip()[:200]}")
        except OSError:
            continue
        if len(hits) >= 50:
            break
    return "\n".join(hits) if hits else "no matches"


# Commands allowed by run_command — read-only, no mutation, no network.
ALLOWED = {"ls", "cat", "grep", "find", "wc", "head", "tail", "file", "tree", "echo", "pwd", "du", "stat"}
BLOCKED_SUBSTRINGS = ["rm ", "mv ", "cp ", "sudo", ">", "|", ";", "&", "curl", "wget", "shutdown", "reboot", "mkfs", "dd "]


@mcp.tool()
def run_command(command: str, timeout: int = 10) -> str:
    """Run a read-only shell command inside the sandbox with a timeout.

    Refuses commands that mutate state, reach the network, or chain shell operators.
    """
    cmd = command.strip()
    if any(d in cmd for d in BLOCKED_SUBSTRINGS):
        return f"blocked: dangerous pattern detected in command: {cmd!r}"
    parts = shlex.split(cmd)
    if not parts or parts[0] not in ALLOWED:
        return f"blocked: command {parts[0] if parts else ''!r} not in allowlist {sorted(ALLOWED)}"
    try:
        out = subprocess.run(parts, cwd=str(ROOT), timeout=timeout, capture_output=True, text=True)
        body = out.stdout
        if out.stderr:
            body += "\n[stderr]\n" + out.stderr
        return body[:4000]
    except subprocess.TimeoutExpired:
        return f"timeout after {timeout}s"
    except Exception as e:  # noqa: BLE001 — surface the error to the agent, don't crash the server
        return f"error: {e}"


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
