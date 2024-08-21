import typing as t


T = t.TypeVar("T")


def minmax(min_value: T, value: T, max_value: T) -> T:
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value
