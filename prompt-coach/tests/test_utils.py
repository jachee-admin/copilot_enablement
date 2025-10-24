from coach.utils import unified_diff
def test_unified_diff_has_headers():
    d = unified_diff("a", "b")
    assert "original" in d and "improved" in d
