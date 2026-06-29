"""Single source of truth for tools, validated at load time.

Pattern source: gstack. Two ideas baked in:
  1. One registry owns names + descriptions + scopes; validate() makes drift a
     load-time crash, not a runtime surprise.
  2. `scope` (AUTHORIZATION) is separate from how a tool is dispatched. A read-shaped
     tool can still require write scope (e.g. it touches disk).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, Set
from .errors import suggest, AgentError


@dataclass
class Tool:
    name: str
    handler: Callable[..., object]
    scope: str = "read"              # authorization category: "read" | "write"
    untrusted_output: bool = False   # output is third-party content -> envelope it
    description: str = ""
    usage: str = ""


class Registry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool: {tool.name}")
        self._tools[tool.name] = tool
        return tool

    def tool(self, name: str, **kw):
        """Decorator. Description defaults to the handler's first docstring line."""
        def deco(fn: Callable[..., object]):
            desc = kw.pop("description", None) or (fn.__doc__ or "").strip().split("\n")[0]
            self.register(Tool(name=name, handler=fn, description=desc, **kw))
            return fn
        return deco

    def get(self, name: str):
        return self._tools.get(name)

    def names(self) -> Set[str]:
        return set(self._tools)

    def validate(self) -> "Registry":
        problems = []
        for t in self._tools.values():
            if not t.description:
                problems.append(f"{t.name}: missing description")
            if t.scope not in ("read", "write"):
                problems.append(f"{t.name}: invalid scope {t.scope!r}")
        if problems:
            raise ValueError("registry validation failed:\n  " + "\n  ".join(problems))
        return self

    def resolve(self, name: str) -> Tool:
        t = self.get(name)
        if t is None:
            s = suggest(name, self.names())
            hint = f"Did you mean '{s}'?" if s else f"Available: {', '.join(sorted(self.names()))}."
            raise AgentError(f"Unknown tool '{name}'.", hint)
        return t
