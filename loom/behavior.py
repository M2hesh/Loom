"""Behavior injection at prompt-assembly time. The harness as text.

Pattern source: ponytail. Profiles are plain strings prepended to the system prompt.
The whole steering mechanism is text injected at the right point in the loop.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Profile:
    name: str
    system_text: str


MINIMAL = Profile(
    "minimal",
    (
        "Operating mode: minimal. Prefer the smallest change that fully solves the task. "
        "Before adding code, check in order: is it needed at all; does existing code, the "
        "standard library, or an installed dependency already do it; can it be one line. Only "
        "then write the minimum. Never trade away input validation at trust boundaries, error "
        "handling, or security to save lines."
    ),
)
DEFAULT = Profile("default", "Operating mode: default. Solve the task directly and completely.")
CAREFUL = Profile(
    "careful",
    (
        "Operating mode: careful. Confirm intent before destructive or irreversible actions. "
        "State your assumptions explicitly. Prefer reversible steps."
    ),
)

PROFILES = {p.name: p for p in (MINIMAL, DEFAULT, CAREFUL)}


def inject(base_system_prompt: str, profile: str = "default", extra: str = "") -> str:
    p = PROFILES.get(profile, DEFAULT)
    parts = [p.system_text, (base_system_prompt or "").strip(), (extra or "").strip()]
    return "\n\n".join(x for x in parts if x)
