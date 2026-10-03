from typing import List


def str_in_list_ignore_case(s: str, l: List[str] | None) -> bool:
    if l is None:
        return False
    return s.lower() in [item.lower() for item in l]
