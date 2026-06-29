"""Dispatch a tool call: authorize, execute, wrap errors and untrusted output.

Pattern source: gstack. Authorization is checked separately from dispatch, errors
come back as recovery instructions, and untrusted (third-party) output is wrapped in
a trust-boundary envelope on the data path — security folded in, not bolted on.
"""
from __future__ import annotations
from typing import Set
from .registry import Registry
from .errors import AgentError


def wrap_untrusted(text: str, source: str) -> str:
    # Break any attacker-supplied end-marker with a zero-width space; strip newlines from source.
    safe = text.replace("--- END UNTRUSTED", "--- END\u200b UNTRUSTED")
    src = source.replace("\n", " ").replace("\r", " ")[:200]
    return (
        f"--- BEGIN UNTRUSTED CONTENT (source: {src}) ---\n"
        f"{safe}\n"
        f"--- END UNTRUSTED CONTENT ---"
    )


def dispatch(registry: Registry, name: str, args: dict, granted: Set[str], source: str = "tool") -> str:
    tool = registry.resolve(name)                 # AgentError w/ suggestion if unknown
    if tool.scope not in granted:                 # authorization != dispatch routing
        raise AgentError(
            f"Tool '{name}' needs '{tool.scope}' scope.",
            f"Grant it or use a read-only alternative. Granted: {sorted(granted)}.",
        )
    try:
        out = tool.handler(**(args or {}))
    except AgentError:
        raise
    except TypeError as e:
        raise AgentError(f"Bad arguments for '{name}': {e}.", f"Usage: {tool.usage or name}")
    except Exception as e:  # noqa: BLE001 - surface any tool failure as a recoverable instruction
        raise AgentError(f"Tool '{name}' failed: {e}.", "Inspect the inputs and retry.")
    out = "" if out is None else str(out)
    return wrap_untrusted(out, source) if tool.untrusted_output else out
