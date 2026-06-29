import pytest
from loom.registry import Registry, Tool
from loom.dispatch import dispatch
from loom.errors import AgentError


def _reg():
    reg = Registry()
    reg.register(Tool(name="read_it", handler=lambda: "ok", scope="read", description="d"))
    reg.register(Tool(name="write_it", handler=lambda x="": x, scope="write", description="d"))
    reg.register(Tool(name="ext", handler=lambda: "third-party data", scope="read",
                      untrusted_output=True, description="d"))
    return reg.validate()


def test_scope_enforced():
    with pytest.raises(AgentError):
        dispatch(_reg(), "write_it", {"x": "y"}, granted={"read"})


def test_scope_granted_runs():
    assert dispatch(_reg(), "write_it", {"x": "y"}, granted={"read", "write"}) == "y"


def test_untrusted_output_wrapped():
    out = dispatch(_reg(), "ext", {}, granted={"read"}, source="http://evil.test")
    assert "BEGIN UNTRUSTED CONTENT" in out and "END UNTRUSTED CONTENT" in out


def test_bad_args_actionable():
    with pytest.raises(AgentError) as ei:
        dispatch(_reg(), "read_it", {"nope": 1}, granted={"read"})
    assert "Usage" in str(ei.value)
