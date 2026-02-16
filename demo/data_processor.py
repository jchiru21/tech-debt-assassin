"""Toy data processing pipeline — zero type annotations."""

from typing import Any


def flatten(nested_list: list[Any]) -> list[Any]:
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def deduplicate(items: list) -> list:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def group_by(records: list[dict[str, object]], key: str) -> dict[object, list[dict[str, object]]]:
    groups = {}
    for record in records:
        k = record[key]
        groups.setdefault(k, []).append(record)
    return groups


def average(numbers: list[float]) -> float:
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)
