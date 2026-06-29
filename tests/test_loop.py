from loom.registry import Registry, Tool
from loom.model import StubModel
from loom.memory import TrajectoryStore
from loom.loop import Agent


def _reg():
    reg = Registry()
    reg.register(Tool(name="echo", handler=lambda text="": text, scope="read", description="d"))
    return reg.validate()


def test_end_to_end_runs_and_records():
    mem = TrajectoryStore()
    agent = Agent(StubModel(plan=[("echo", {"text": "hello"})]), _reg(), mem,
                  granted_scopes=("read",))
    res = agent.run("say hello")
    assert res.output == "Task complete."
    kinds = [s.kind for s in res.steps]
    assert "tool" in kinds and "final" in kinds
    assert len(mem) == 1   # successful run recorded


def test_unknown_tool_becomes_recoverable_error():
    agent = Agent(StubModel(plan=[("ecko", {"text": "x"})]), _reg(), None,
                  granted_scopes=("read",))
    res = agent.run("typo tool")
    assert any(s.kind == "error" for s in res.steps)
