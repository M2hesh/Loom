"""The agent loop — wires behavior + memory + model + dispatch + compression.

This is the spine. Read top to bottom and you can see every intervention point from
the four projects firing in order, once per turn.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from .behavior import inject
from .dispatch import dispatch
from .compress import compress
from .errors import AgentError


@dataclass
class Step:
    kind: str   # "tool" | "final" | "error"
    detail: str


@dataclass
class Result:
    task: str
    output: str
    steps: List[Step] = field(default_factory=list)
    tokens_saved: int = 0


class Agent:
    def __init__(
        self,
        model,
        registry,
        memory=None,
        *,
        profile: str = "default",
        granted_scopes=("read",),
        compress_level: str = "default",
        max_steps: int = 12,
        base_system: Optional[str] = None,
    ):
        self.model = model
        self.registry = registry
        self.memory = memory
        self.profile = profile
        self.granted = set(granted_scopes)
        self.compress_level = compress_level
        self.max_steps = max_steps
        self.base_system = base_system or "You are an agent. Use tools to accomplish the task, then stop."

    def assemble_system(self, task: str) -> str:
        extra = ""
        if self.memory is not None:
            hits = self.memory.retrieve(task, k=3)
            if hits:
                lines = [
                    f"- (relevance {h.relevance:.2f}) {h.trajectory.task} -> {h.trajectory.outcome}"
                    for h in hits
                ]
                extra = "Relevant past trajectories (reference only, may be stale):\n" + "\n".join(lines)
        return inject(self.base_system, self.profile, extra)

    def run(self, task: str) -> Result:
        system = self.assemble_system(task)
        history: List[dict] = [{"role": "user", "content": task}]
        res = Result(task=task, output="")
        for _ in range(self.max_steps):
            rsp = self.model.complete(system, history)
            if rsp.tool_call:
                try:
                    raw = dispatch(self.registry, rsp.tool_call.name, rsp.tool_call.args, self.granted)
                    c = compress(raw, self.compress_level)
                    res.tokens_saved += c.tokens_before - c.tokens_after
                    history.append(
                        {"role": "assistant", "content": f"[tool {rsp.tool_call.name}] {c.text}"}
                    )
                    res.steps.append(Step("tool", f"{rsp.tool_call.name} (saved {c.saved_pct}%)"))
                except AgentError as e:
                    history.append({"role": "user", "content": str(e)})  # errors-as-prompts
                    res.steps.append(Step("error", str(e)))
                continue
            res.output = rsp.text
            res.steps.append(Step("final", rsp.text))
            break
        else:
            res.output = "Stopped: max steps reached."
            res.steps.append(Step("error", res.output))

        if self.memory is not None:
            quality = 1.0 if any(s.kind == "final" for s in res.steps) else 0.3
            self.memory.record(task, res.output, quality)
        return res
