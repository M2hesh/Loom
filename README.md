# loom

**A minimal, adaptable agent harness.** It distills the genuinely good ideas from four
agentic-coding projects — [gstack](https://github.com/garrytan/gstack),
[ponytail](https://github.com/DietrichGebert/ponytail),
[RTK](https://github.com/rtk-ai/rtk), and [ruflo](https://github.com/ruvnet/ruflo) —
into one small, readable codebase you can fork and grow.

> Agent = Model + Harness. The model reasons; the harness gives it tools, memory,
> behavior, and efficiency. **loom is the harness.**

It runs end-to-end with **zero dependencies** (pure standard library) and **no API key**,
using a deterministic stub model, so you can read the whole loop fire before wiring in a
real LLM.

```bash
python examples/demo.py        # see all four patterns work, offline
python -m pytest -q            # 19 tests, ~0.06s
python -m loom run "say hi"    # the CLI
```

## The one idea that organizes everything

A harness intervenes at points in the agent loop. loom has one module per intervention:

```
assemble prompt ── model ── tool call ── run tool ── compress output ── append ── repeat
   │                          │                          │                │
behavior.py +              dispatch.py               compress.py      errors.py
memory.py                  (+ registry.py)           (RTK)            (errors-as-prompts)
   (ponytail / ruflo)      (gstack)                                   (gstack)

skills.py  ── choreography across whole runs, via a shared artifact store (gstack)
loop.py    ── the spine that wires it all together
```

## Where each idea comes from

| Module | Pattern | Borrowed from | What it does |
|---|---|---|---|
| `registry.py` | Single source of truth, validated at load | gstack | One registry owns names/descriptions/scopes; `validate()` makes drift a load-time crash. Authorization (`scope`) is **decoupled** from dispatch routing. |
| `dispatch.py` | Errors-as-prompts + trust envelope | gstack | Unknown tool → "did you mean?"; failures come back as recovery instructions; untrusted (third-party) output is wrapped on the data path. |
| `compress.py` | Output compression | RTK | Collapses runs of low-signal lines, keeps error/diff lines verbatim. Lossless on signal, lossy on noise. |
| `behavior.py` | Harness-as-text | ponytail | Behavior profiles (`minimal` / `default` / `careful`) injected into the system prompt at assembly time. The whole steering mechanism is text at the right point in the loop. |
| `memory.py` | Trajectory retrieval | ruflo (SONA / ReasoningBank) | Stores `(task, outcome, quality)` and retrieves by cosine similarity. **Honestly scoped: this is retrieval, not model fine-tuning.** |
| `skills.py` | Choreography-by-artifact | gstack | Skills coordinate through a shared artifact store, not a central scheduler. Data-dependency ordering, fail-fast on deadlock. |
| `loop.py` | The agent loop | (synthesis) | Wires behavior + memory + dispatch + compression into one turn, with errors fed back as prompts. |

## Adapt it

**Plug in a real model.** The loop only needs `.complete(system, history) -> ModelResponse`.

```python
from loom import Agent, AnthropicModel   # pip install "loom[anthropic]" + ANTHROPIC_API_KEY
agent = Agent(AnthropicModel("claude-sonnet-4-6"), registry, memory, profile="minimal")
```

Extend `AnthropicModel.complete` to parse `tool_use` blocks into a `ToolCall` for real
tool calling against your `Registry`.

**Add a tool** (scope and untrusted-ness are first-class):

```python
@reg.tool("read_db", scope="read", description="Run a read-only SQL query.")
def read_db(sql: str) -> str:
    ...
reg.validate()   # fails loudly now if anything is misdeclared
```

**Add a compression filter** for your domain — subclass `Filter`, register it in `LEVELS`.

**Use a real embedder** — pass any object with `.embed(text) -> list[float]` to
`TrajectoryStore(embedder=...)`. The default `HashingEmbedder` is dependency-free so the
kit runs anywhere; swap it for sentence-transformers / an embeddings API in production.

**Chain skills, from markdown to files on disk.** Edit the specs in `skills/*.md`
(front-matter declares `name`/`reads`/`writes`; the prose body is the instruction),
load them, run the chain, and persist artifacts:

```python
from loom import load_skills, run_chain

# bind each spec to deterministic Python logic...
skills = load_skills("skills", handlers={"plan": my_plan_fn, ...})
# ...or let each spec's prose body drive a real model:
# skills = load_skills("skills", model=AnthropicModel("claude-sonnet-4-6"))

store, order = run_chain(skills, persist_dir="artifacts")
store["design_doc"]            # in memory
# artifacts/design_doc.md      # and on disk — strings -> .md, else -> .json
```

A skill with no handler and no model raises a loud, actionable error when run, so a
half-wired chain never silently produces nothing. See `examples/skills_demo.py`.

## What loom deliberately does NOT do

The teardown that produced this kit found that the flashiest claims in this space are
where existence outruns usefulness. So, on purpose:

- **No fake self-learning.** `memory.py` is retrieval. It cannot fine-tune a closed API
  model, so it doesn't pretend to — it influences the agent only by injecting relevant
  past trajectories into context.
- **No multi-machine consensus.** Real Raft/Byzantine engines exist elsewhere; almost no
  single-builder workflow needs them, and shipping one you never load is how repos bloat.
- **No daemon, browser, or native binaries.** Those are real gstack/RTK engineering, but
  they're environment-specific. loom stays pure-Python so it's the substrate you extend,
  not a platform you adopt.

Keep it small. Add only the rung the task actually needs. (Yes — the `minimal` profile
applies to loom itself.)

MIT licensed.
