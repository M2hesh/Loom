import pytest
from loom.registry import Registry, Tool
from loom.errors import AgentError


def test_validate_catches_missing_description():
    reg = Registry()
    reg.register(Tool(name="bad", handler=lambda: "x", description=""))
    with pytest.raises(ValueError):
        reg.validate()


def test_validate_catches_bad_scope():
    reg = Registry()
    reg.register(Tool(name="bad", handler=lambda: "x", scope="admin", description="d"))
    with pytest.raises(ValueError):
        reg.validate()


def test_resolve_suggests_close_name():
    reg = Registry()
    reg.register(Tool(name="snapshot", handler=lambda: "x", description="d"))
    with pytest.raises(AgentError) as ei:
        reg.resolve("snapshat")
    assert "snapshot" in str(ei.value)


def test_decorator_uses_docstring():
    reg = Registry()

    @reg.tool("greet", scope="read")
    def greet():
        "Say hello to the user."
        return "hi"

    reg.validate()
    assert reg.get("greet").description == "Say hello to the user."
