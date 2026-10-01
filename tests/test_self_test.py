from otripy import self_test


def test_self_test_passes(qapp, tmp_path):
    report = tmp_path / "report.txt"
    assert self_test.run(report) == 0
    text = report.read_text(encoding="utf-8")
    assert "All checks passed" in text
    for function in self_test.CHECKS:
        assert f"OK   {function.__name__}" in text
