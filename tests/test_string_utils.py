from app.utils.string_utils import any_substr_in_str_ignore_case, str_in_list_ignore_case


def test_str_in_list_ignore_case_matches_different_case():
    assert str_in_list_ignore_case("BEATLES", ["beatles", "queen"])


def test_str_in_list_ignore_case_no_match():
    assert not str_in_list_ignore_case("NIRVANA", ["beatles", "queen"])


def test_str_in_list_ignore_case_empty_list():
    assert not str_in_list_ignore_case("BEATLES", [])


def test_str_in_list_ignore_case_none_list():
    assert not str_in_list_ignore_case("BEATLES", None)


def test_any_substr_in_str_ignore_case_matches_substring():
    assert any_substr_in_str_ignore_case("Wu-Tang Clan", ["wu-tang", "dr. dre"])


def test_any_substr_in_str_ignore_case_no_match():
    assert not any_substr_in_str_ignore_case("Wu-Tang Clan", ["dr. dre", "queen"])


def test_any_substr_in_str_ignore_case_empty_list():
    assert not any_substr_in_str_ignore_case("Wu-Tang Clan", [])


def test_any_substr_in_str_ignore_case_none_list():
    assert not any_substr_in_str_ignore_case("Wu-Tang Clan", None)
