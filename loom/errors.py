"""Actionable, agent-readable errors.

Pattern source: gstack ("errors are for agents, not humans"). Every error carries
a recovery instruction the model can act on, plus a Levenshtein "did you mean?".
"""
from __future__ import annotations
from typing import Iterable, Optional


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def suggest(name: str, candidates: Iterable[str], max_dist: int = 2) -> Optional[str]:
    """Closest candidate within max_dist. Guarded on length to avoid noisy 2-char matches."""
    if len(name) < 4:
        return None
    best, best_d = None, max_dist + 1
    for cand in sorted(candidates):
        d = levenshtein(name, cand)
        if d <= max_dist and d < best_d:
            best, best_d = cand, d
    return best


class AgentError(Exception):
    """An error phrased so the model can recover without a human."""

    def __init__(self, message: str, hint: Optional[str] = None):
        self.message = message
        self.hint = hint
        super().__init__(message if not hint else f"{message} {hint}")
