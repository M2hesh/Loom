import pytest
from loom.skills import Skill, run_chain
from loom.errors import AgentError


def test_runs_in_dependency_order():
    a = Skill("plan", run=lambda _in: {"plan": "do X"}, writes=("plan",))
    b = Skill("build", run=lambda _in: {"code": _in["plan"] + " -> code"}, reads=("plan",), writes=("code",))
    store, order = run_chain([b, a])     # deliberately out of order
    assert order == ["plan", "build"]
    assert store["code"] == "do X -> code"


def test_stalls_on_missing_dependency():
    b = Skill("build", run=lambda _in: {"code": "x"}, reads=("missing",), writes=("code",))
    with pytest.raises(AgentError):
        run_chain([b])
