from loom.errors import levenshtein, suggest


def test_levenshtein():
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("abc", "abc") == 0


def test_suggest_close():
    assert suggest("snapshat", {"snapshot", "click", "scroll"}) == "snapshot"


def test_suggest_ignores_short_input():
    assert suggest("js", {"is", "ls"}) is None
