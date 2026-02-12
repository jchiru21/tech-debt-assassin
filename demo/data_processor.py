"""Toy data processing pipeline — zero type annotations."""


def flatten(nested_list):
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def deduplicate(items):
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def group_by(records, key):
    groups = {}
    for record in records:
        k = record[key]
        groups.setdefault(k, []).append(record)
    return groups


def average(numbers):
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)
