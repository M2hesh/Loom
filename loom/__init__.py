"""loom — a minimal, adaptable agent harness.

Agent = Model + Harness. The model reasons; the harness gives it tools, memory,
behavior, and efficiency. loom is the harness, organized around the agent loop:

    assemble prompt -> model -> tool call -> run tool -> compress output -> append -> repeat
        ^behavior(+memory)        ^registry/dispatch        ^compress         ^errors-as-prompts

Each module owns one intervention point. Swap any piece; the rest stays put.
"""
from .registry import Registry, Tool
from .dispatch import dispatch, wrap_untrusted
from .compress import compress, Compressed
from .behavior import inject, PROFILES
from .memory import TrajectoryStore, HashingEmbedder
from .model import StubModel, AnthropicModel, ModelResponse, ToolCall
from .loop import Agent, Result, Step
from .skills import Skill, run_chain
from .skill_loader import load_skill, load_skills, parse_spec, spec_to_skill, SkillSpec
from .errors import AgentError, suggest, levenshtein

__version__ = "0.1.0"
__all__ = [
    "Registry", "Tool", "dispatch", "wrap_untrusted", "compress", "Compressed",
    "inject", "PROFILES", "TrajectoryStore", "HashingEmbedder", "StubModel",
    "AnthropicModel", "ModelResponse", "ToolCall", "Agent", "Result", "Step",
    "Skill", "run_chain", "load_skill", "load_skills", "parse_spec", "spec_to_skill",
    "SkillSpec", "AgentError", "suggest", "levenshtein",
]
