"""Choreography-by-artifact: skills coordinate through a shared artifact store.

Pattern source: gstack. There is no central scheduler. Each skill declares the
artifacts it reads and writes; the runner orders them by data dependency and fails
fast (with a recovery hint) if dependencies can never be met. This is orchestration
as stigmergy — agents coordinating by leaving traces, the way ants use trails.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from .errors import AgentError


@dataclass
class Skill:
    name: str
    run: Callable[[dict], dict]   # receives {artifact: value} for its reads; returns artifacts to write
    reads: Tuple[str, ...] = ()
    writes: Tuple[str, ...] = ()
    description: str = ""


def _persist(store: Dict[str, object], keys: List[str], persist_dir: str) -> List[str]:
    """Write produced artifacts to disk: strings -> <key>.md, everything else -> <key>.json."""
    d = Path(persist_dir)
    d.mkdir(parents=True, exist_ok=True)
    written: List[str] = []
    for k in keys:
        v = store.get(k)
        if isinstance(v, str):
            p = d / f"{k}.md"
            p.write_text(v)
        else:
            p = d / f"{k}.json"
            p.write_text(json.dumps(v, indent=2, default=str))
        written.append(str(p))
    return written


def run_chain(
    skills: List[Skill],
    artifacts: Dict[str, object] = None,
    *,
    persist_dir: Optional[str] = None,
):
    """Run skills as their reads become available. Returns (final_store, run_order).

    If `persist_dir` is set, every artifact a skill *produces* is also written to disk
    there — so `design_doc` becomes `<persist_dir>/design_doc.md`, matching gstack's
    file-on-disk behavior. Seed artifacts passed in via `artifacts` are not persisted.
    """
    store: Dict[str, object] = dict(artifacts or {})
    pending = list(skills)
    order: List[str] = []
    produced_keys: List[str] = []
    progress = True
    while pending and progress:
        progress = False
        for sk in list(pending):
            if all(r in store for r in sk.reads):
                inputs = {r: store[r] for r in sk.reads}
                produced = sk.run(inputs) or {}
                for w in sk.writes:
                    if w not in produced:
                        raise AgentError(
                            f"Skill '{sk.name}' promised artifact '{w}' but did not produce it.",
                            "Return every declared write from the skill's run().",
                        )
                store.update(produced)
                produced_keys.extend(sk.writes)
                order.append(sk.name)
                pending.remove(sk)
                progress = True
    if pending:
        missing = {sk.name: [r for r in sk.reads if r not in store] for sk in pending}
        raise AgentError("Choreography stalled — unmet artifact dependencies.", f"Blocked: {missing}")
    if persist_dir:
        _persist(store, produced_keys, persist_dir)
    return store, order
