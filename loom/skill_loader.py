"""Load skill specs from markdown into executable Skill objects.

This closes the gap between the `skills/*.md` *specs* (front-matter + prose) and the
runnable `Skill` objects `run_chain` expects. Two ways to give a parsed spec a `run`:

  1. handlers  — a {name: callable} map for deterministic Python logic (offline, no LLM).
  2. model     — a model with .complete(system, history); the skill's prose body becomes
                 the system prompt, its `reads` become context, and the model's text fills
                 its `writes`. This mirrors gstack, where a skill's prose *is* the behavior.

If neither is supplied, the loaded skill raises an actionable error when run, so a
half-wired chain fails loudly instead of silently producing nothing.

Placement note: this lives inside the `loom` package (importable) rather than in the
`skills/` directory, which stays pure specs/data.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .skills import Skill
from .errors import AgentError


@dataclass
class SkillSpec:
    name: str
    reads: Tuple[str, ...]
    writes: Tuple[str, ...]
    body: str
    source: str = ""


def _parse_list(val: str) -> Tuple[str, ...]:
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        return tuple(x.strip() for x in inner.split(",") if x.strip())
    return (val,) if val else ()


def parse_spec(text: str, source: str = "") -> SkillSpec:
    """Parse `---\\n<front-matter>\\n---\\n<body>` into a SkillSpec."""
    if not text.lstrip().startswith("---"):
        raise AgentError(
            f"Skill spec {source or '(inline)'} has no front-matter.",
            "Start the file with a '---' fenced block declaring name/reads/writes.",
        )
    parts = text.split("---", 2)  # ['', front-matter, body]
    if len(parts) < 3:
        raise AgentError(
            f"Skill spec {source or '(inline)'} front-matter is not closed.",
            "Wrap the metadata in a pair of '---' lines.",
        )
    meta: Dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        meta[key.strip()] = val.strip()

    name = meta.get("name", "").strip()
    if not name:
        raise AgentError(f"Skill spec {source or '(inline)'} is missing 'name'.", "Add 'name: <slug>'.")
    return SkillSpec(
        name=name,
        reads=_parse_list(meta.get("reads", "[]")),
        writes=_parse_list(meta.get("writes", "[]")),
        body=parts[2].strip(),
        source=source,
    )


def _model_runner(spec: SkillSpec, model) -> Callable[[dict], dict]:
    def run(inputs: dict) -> dict:
        context = "\n\n".join(f"## {k}\n{v}" for k, v in inputs.items()) or "(no input artifacts)"
        rsp = model.complete(
            spec.body,  # the prose instruction is the system prompt
            [{"role": "user", "content": f"{context}\n\nProduce the required output."}],
        )
        text = getattr(rsp, "text", "") or ""
        if len(spec.writes) <= 1:
            return {spec.writes[0]: text} if spec.writes else {}
        # multi-write: the model must return JSON keyed by the declared writes
        try:
            data = json.loads(text)
            return {w: data[w] for w in spec.writes}
        except Exception as e:  # noqa: BLE001
            raise AgentError(
                f"Skill '{spec.name}' declares {len(spec.writes)} writes but model output "
                f"wasn't JSON with keys {list(spec.writes)}: {e}.",
                "Have the skill body instruct the model to return a JSON object, or split it.",
            )

    return run


def _unbound_runner(spec: SkillSpec) -> Callable[[dict], dict]:
    def run(_inputs: dict) -> dict:
        raise AgentError(
            f"Skill '{spec.name}' has no implementation.",
            "Pass a handler ({name: fn}) or a model to load_skills().",
        )

    return run


def spec_to_skill(spec: SkillSpec, model=None, handlers: Optional[Dict[str, Callable]] = None) -> Skill:
    if handlers and spec.name in handlers:
        run = handlers[spec.name]
    elif model is not None:
        run = _model_runner(spec, model)
    else:
        run = _unbound_runner(spec)
    return Skill(
        name=spec.name,
        run=run,
        reads=spec.reads,
        writes=spec.writes,
        description=spec.body.splitlines()[0].lstrip("# ").strip() if spec.body else "",
    )


def load_skill(path, model=None, handlers: Optional[Dict[str, Callable]] = None) -> Skill:
    p = Path(path)
    return spec_to_skill(parse_spec(p.read_text(), source=p.name), model=model, handlers=handlers)


def load_skills(directory, model=None, handlers: Optional[Dict[str, Callable]] = None) -> List[Skill]:
    """Load every `*.md` skill in a directory (sorted by filename)."""
    d = Path(directory)
    if not d.is_dir():
        raise AgentError(f"Skill directory not found: {directory}.", "Point at a folder of *.md specs.")
    return [load_skill(p, model=model, handlers=handlers) for p in sorted(d.glob("*.md"))]
