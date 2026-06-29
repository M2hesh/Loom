"""loom CLI: run | validate | skills."""
from __future__ import annotations
import argparse
import sys
from .registry import Registry
from .model import StubModel
from .memory import TrajectoryStore
from .loop import Agent


def _demo_registry() -> Registry:
    reg = Registry()

    @reg.tool("echo", scope="read", description="Echo the given text back.")
    def echo(text: str = "") -> str:
        return text

    return reg.validate()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="loom", description="Minimal adaptable agent harness.")
    sub = p.add_subparsers(dest="cmd")
    r = sub.add_parser("run", help="Run the demo agent on a task.")
    r.add_argument("task")
    sub.add_parser("validate", help="Validate the demo registry (load-time invariant).")

    args = p.parse_args(argv)
    if args.cmd == "validate":
        _demo_registry()
        print("registry OK")
        return 0
    if args.cmd == "run":
        reg = _demo_registry()
        agent = Agent(
            StubModel(plan=[("echo", {"text": args.task})]),
            reg,
            TrajectoryStore(),
            granted_scopes=("read",),
        )
        res = agent.run(args.task)
        print(res.output)
        for s in res.steps:
            print(f"  [{s.kind}] {s.detail}")
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
