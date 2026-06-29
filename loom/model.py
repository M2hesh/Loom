"""Pluggable model. StubModel runs the whole kit offline; AnthropicModel is the real hook.

The loop depends only on the .complete(system, history) -> ModelResponse contract, so
any backend (Anthropic, OpenAI, a local model, or the stub) drops in.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ToolCall:
    name: str
    args: dict


@dataclass
class ModelResponse:
    text: str = ""
    tool_call: Optional[ToolCall] = None
    done: bool = False


class StubModel:
    """Deterministic offline model: replays a fixed plan of tool calls, then finishes.

    `plan` is a list of (tool_name, args) tuples. Used for demos and tests so the whole
    harness runs with no API key.
    """

    def __init__(self, plan=None, final_text: str = "Task complete."):
        self._plan = list(plan or [])
        self._final = final_text
        self._step = 0

    def complete(self, system: str, history: List[dict]) -> ModelResponse:
        if self._step < len(self._plan):
            name, args = self._plan[self._step]
            self._step += 1
            return ModelResponse(tool_call=ToolCall(name, args))
        return ModelResponse(text=self._final, done=True)


class AnthropicModel:
    """Real model via the anthropic SDK. Requires `pip install anthropic` + ANTHROPIC_API_KEY.

    This is a minimal text-only mapping; extend `complete` to parse tool_use blocks for
    real tool calling against your Registry.
    """

    def __init__(self, model: str = "claude-sonnet-4-6", max_tokens: int = 1024):
        try:
            import anthropic  # noqa: F401
        except ImportError as e:
            raise RuntimeError("AnthropicModel needs `pip install anthropic`.") from e
        import anthropic
        self._client = anthropic.Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, system: str, history: List[dict]) -> ModelResponse:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=history,
        )
        text = "".join(getattr(b, "text", "") for b in msg.content)
        return ModelResponse(text=text, done=True)
