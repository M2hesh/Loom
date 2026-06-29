from loom.memory import TrajectoryStore


def test_retrieves_nearest():
    store = TrajectoryStore()
    store.record("optimize a github actions stock pipeline", "added caching", 1.0)
    store.record("bake a chocolate cake", "used cocoa", 1.0)
    hits = store.retrieve("speed up my github actions pipeline", k=1)
    assert hits and "github actions" in hits[0].trajectory.task


def test_quality_gate_drops_low_quality():
    store = TrajectoryStore(min_quality=0.5)
    assert store.record("x", "y", 0.3) is None
    assert len(store) == 0
