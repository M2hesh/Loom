from loom.compress import compress


def test_collapses_noise_keeps_signal():
    lines = ["test_%d PASSED" % i for i in range(200)]
    lines.insert(100, "test_99 FAILED: assertion error")
    text = "\n".join(lines)
    c = compress(text, "default")
    assert "FAILED" in c.text                 # signal preserved
    assert "lines elided" in c.text           # noise collapsed
    assert c.tokens_after < c.tokens_before   # net reduction
    assert c.saved_pct > 50


def test_off_is_passthrough():
    text = "a\nb\nc"
    c = compress(text, "off")
    assert c.text == text
