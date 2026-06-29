"""Output compression at the tool-output boundary.

Pattern source: RTK. Lossless on signal, lossy on noise: long runs of low-signal
lines collapse, while lines that look like errors/failures/diffs are kept in place
and in full. Strategy pattern so you can add domain-specific filters.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List

SIGNAL = re.compile(
    r"(\b(error|fail|failed|failure|exception|traceback|warning|denied|panic|fatal)\b|^[+-]\s|^@@)",
    re.IGNORECASE,
)


def est_tokens(s: str) -> int:
    return max(1, len(s) // 4)


@dataclass
class Compressed:
    text: str
    tokens_before: int
    tokens_after: int

    @property
    def saved_pct(self) -> float:
        if not self.tokens_before:
            return 0.0
        return round(100 * (1 - self.tokens_after / self.tokens_before), 1)


class Filter:
    def apply(self, text: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class Passthrough(Filter):
    def apply(self, text: str) -> str:
        return text


class CollapseRuns(Filter):
    """Collapse consecutive low-signal lines; keep signal lines verbatim, in order."""

    def __init__(self, keep_head: int = 4, keep_tail: int = 2):
        self.keep_head, self.keep_tail = keep_head, keep_tail

    def _flush(self, run: List[str]) -> List[str]:
        if len(run) <= self.keep_head + self.keep_tail:
            return run
        hidden = len(run) - self.keep_head - self.keep_tail
        return run[: self.keep_head] + [f"... {hidden} lines elided ..."] + run[-self.keep_tail :]

    def apply(self, text: str) -> str:
        out: List[str] = []
        run: List[str] = []
        for ln in text.splitlines():
            if SIGNAL.search(ln):
                out += self._flush(run)
                run = []
                out.append(ln)
            else:
                run.append(ln)
        out += self._flush(run)
        return "\n".join(out)


LEVELS = {
    "off": Passthrough(),
    "default": CollapseRuns(),
    "aggressive": CollapseRuns(keep_head=2, keep_tail=1),
}


def compress(text: str, level: str = "default") -> Compressed:
    f = LEVELS.get(level, LEVELS["default"])
    before = est_tokens(text)
    out = f.apply(text)
    return Compressed(out, before, est_tokens(out))
