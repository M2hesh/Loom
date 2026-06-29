import os
import pytest
from loom.skill_loader import parse_spec, load_skills
from loom.skills import run_chain
from loom.errors import AgentError

SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills")


def test_parse_spec_reads_frontmatter():
    text = "---\nname: plan\nreads: []\nwrites: [design_doc]\n---\n# plan\nTurn vague into a doc."
    spec = parse_spec(text)
    assert spec.name == "plan"
    assert spec.reads == ()
    assert spec.writes == ("design_doc",)
    assert "Turn vague" in spec.body


def test_parse_spec_requires_frontmatter():
    with pytest.raises(AgentError):
        parse_spec("# no front matter here")


def test_load_real_specs_and_run_with_handlers(tmp_path):
    handlers = {
        "plan": lambda _in: {"design_doc": "DOC"},
        "build": lambda inp: {"diff": "DIFF:" + inp["design_doc"]},
        "review": lambda inp: {"review_notes": "OK:" + inp["diff"]},
    }
    skills = load_skills(SKILLS_DIR, handlers=handlers)
    names = {s.name for s in skills}
    assert {"plan", "build", "review"} <= names

    store, order = run_chain(skills, persist_dir=str(tmp_path))
    # dependency ordering: plan before build before review
    assert order.index("plan") < order.index("build") < order.index("review")
    assert store["design_doc"] == "DOC"

    # design_doc is now a real file on disk
    doc = tmp_path / "design_doc.md"
    assert doc.exists() and doc.read_text() == "DOC"


def test_unbound_skill_fails_loudly():
    skills = load_skills(SKILLS_DIR)  # no handlers, no model
    plan = next(s for s in skills if s.name == "plan")
    with pytest.raises(AgentError):
        plan.run({})


def test_model_backed_runner_fills_single_write():
    from loom.model import StubModel
    skills = load_skills(SKILLS_DIR, model=StubModel(final_text="generated doc"))
    plan = next(s for s in skills if s.name == "plan")
    assert plan.run({}) == {"design_doc": "generated doc"}
