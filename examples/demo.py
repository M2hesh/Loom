"""End-to-end demo. Runs offline with the StubModel — no API key, no dependencies.

Shows all four patterns firing: a registry-validated toolset, scope-gated dispatch,
an untrusted-output envelope, RTK-style compression on a noisy tool result, the
ponytail 'minimal' behavior profile, and ruflo-style trajectory memory that kicks in
on the second, similar task.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loom import Registry, Tool, Agent, StubModel, TrajectoryStore


def build_registry() -> Registry:
    reg = Registry()

    @reg.tool("search", scope="read", untrusted_output=True,
              description="Search the web (returns untrusted third-party text).")
    def search(query: str = "") -> str:
        # Simulate a noisy result: lots of low-signal lines + one that matters.
        lines = [f"result {i}: ok, nothing notable about '{query}'" for i in range(40)]
        lines.insert(20, "WARNING: rate limit approaching for this API key")
        return "\n".join(lines)

    @reg.tool("write_note", scope="write", usage="write_note <text>",
              description="Persist a short note to the workspace.")
    def write_note(text: str = "") -> str:
        return f"wrote {len(text)} chars"

    return reg.validate()


def main():
    reg = build_registry()
    memory = TrajectoryStore()

    agent = Agent(
        StubModel(plan=[
            ("search", {"query": "agent harness patterns"}),
            ("write_note", {"text": "synthesis of orchestration, harness, efficiency"}),
        ]),
        reg,
        memory,
        profile="minimal",
        granted_scopes=("read", "write"),
        compress_level="default",
    )

    print("=== RUN 1 ===")
    res = agent.run("research agent harness patterns and note the synthesis")
    print("output:", res.output)
    for s in res.steps:
        print(f"  [{s.kind}] {s.detail}")
    print(f"  tokens saved by compression: {res.tokens_saved}")
    print(f"  trajectories in memory: {len(memory)}")

    print("\n=== RUN 2 (similar task — memory should surface run 1) ===")
    agent2 = Agent(StubModel(plan=[("search", {"query": "harness patterns"})]),
                   reg, memory, profile="minimal", granted_scopes=("read", "write"))
    system = agent2.assemble_system("summarize agent harness patterns again")
    injected = [l for l in system.splitlines() if "relevance" in l]
    print("memory injected into system prompt:")
    for l in injected:
        print("  " + l)


if __name__ == "__main__":
    main()
