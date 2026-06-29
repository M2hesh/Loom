"""Load the markdown skill specs, run the chain, and persist artifacts to disk.

Shows the gap closed: skills/*.md -> executable Skill objects -> run_chain -> real files.
Runs offline using deterministic handlers (no model needed). Swap `handlers=` for
`model=AnthropicModel(...)` to let each skill's prose body drive a real LLM instead.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from loom import load_skills, run_chain

SKILLS_DIR = os.path.join(ROOT, "skills")
OUT_DIR = os.path.join(ROOT, "artifacts")


# Deterministic handlers so the offline demo produces meaningful artifacts.
def plan(_inputs):
    doc = (
        "# Design: rate-limit-safe search\n\n"
        "Reframe: the task isn't 'add search', it's 'don't get throttled mid-run'.\n\n"
        "Three smallest slices:\n"
        "1. Cache identical queries for the session.\n"
        "2. Back off on the rate-limit warning the API already emits.\n"
        "3. Batch related queries into one call.\n\n"
        "Recommendation: ship slice 1 first — smallest change, removes most repeat calls."
    )
    return {"design_doc": doc}


def build(inputs):
    return {"diff": f"# diff\nImplemented slice 1 (session cache) per:\n\n{inputs['design_doc'][:60]}..."}


def review(inputs):
    return {"review_notes": f"Reviewed diff ({len(inputs['diff'])} chars). LGTM; add a cache-size cap."}


def main():
    skills = load_skills(SKILLS_DIR, handlers={"plan": plan, "build": build, "review": review})
    print("loaded skills:", [s.name for s in skills])

    store, order = run_chain(skills, persist_dir=OUT_DIR)
    print("ran in order:", order)
    print("\ndesign_doc is now a real file:")
    path = os.path.join(OUT_DIR, "design_doc.md")
    print("  ->", path)
    print("---")
    print(open(path).read())


if __name__ == "__main__":
    main()
