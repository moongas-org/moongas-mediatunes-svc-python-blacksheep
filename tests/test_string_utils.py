from app.utils.string_utils import str_in_list_ignore_case


def test_str_in_list_ignore_case_matches_different_case():
    assert str_in_list_ignore_case("BEATLES", ["beatles", "queen"])


def test_str_in_list_ignore_case_no_match():
    assert not str_in_list_ignore_case("NIRVANA", ["beatles", "queen"])


def test_str_in_list_ignore_case_empty_list():
    assert not str_in_list_ignore_case("BEATLES", [])


def test_str_in_list_ignore_case_none_list():
    assert not str_in_list_ignore_case("BEATLES", None)
