from typing import List


def str_in_list_ignore_case(s: str, l: List[str] | None) -> bool:
    if l is None:
        return False
    return s.lower() in [item.lower() for item in l]


def any_substr_in_str_ignore_case(s: str, substrings: List[str] | None) -> bool:
    if substrings is None:
        return False
    s_lower = s.lower()
    return any(item.lower() in s_lower for item in substrings)
