"""Trajectory memory = retrieval over past runs. NOT model fine-tuning.

Pattern source: ruflo's SONA/ReasoningBank, scoped honestly. We store (task, outcome,
quality) with a cheap local embedding and retrieve by cosine similarity. This can only
influence the agent by injecting relevant past trajectories into context; it never
changes the underlying model. Swap HashingEmbedder for a real embedder in production.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

_TOK = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> List[str]:
    return _TOK.findall(s.lower())


class HashingEmbedder:
    """Zero-dependency deterministic embedding: L2-normalized hashed bag-of-tokens."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        v = [0.0] * self.dim
        for tok in _tokens(text):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            v[h % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]


def cosine(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


@dataclass
class Trajectory:
    task: str
    outcome: str
    quality: float
    embedding: List[float]


@dataclass
class Retrieved:
    trajectory: Trajectory
    relevance: float


class TrajectoryStore:
    def __init__(self, embedder=None, path: Optional[str] = None, min_quality: float = 0.5):
        self.embedder = embedder or HashingEmbedder()
        self.path = Path(path) if path else None
        self.min_quality = min_quality
        self._items: List[Trajectory] = []
        if self.path and self.path.exists():
            self._load()

    def record(self, task: str, outcome: str, quality: float) -> Optional[Trajectory]:
        if quality < self.min_quality:  # quality gate, like SONA's threshold
            return None
        t = Trajectory(task, outcome, float(quality), self.embedder.embed(task))
        self._items.append(t)
        if self.path:
            self._save()
        return t

    def retrieve(self, query: str, k: int = 3) -> List[Retrieved]:
        if not self._items:
            return []
        q = self.embedder.embed(query)
        scored = [Retrieved(t, cosine(q, t.embedding)) for t in self._items]
        scored.sort(key=lambda r: r.relevance, reverse=True)
        return [r for r in scored[:k] if r.relevance > 0.0]

    def __len__(self) -> int:
        return len(self._items)

    def _save(self) -> None:
        self.path.write_text(json.dumps([asdict(t) for t in self._items]))

    def _load(self) -> None:
        self._items = [Trajectory(**d) for d in json.loads(self.path.read_text())]
