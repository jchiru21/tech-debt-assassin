"""String manipulation helpers — completely untyped."""


def reverse_string(s: str) -> str:
    return s[::-1]


def count_vowels(text: str) -> int:
    return sum(1 for ch in text.lower() if ch in "aeiou")


def truncate(text: str, max_length: int, suffix: str) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def is_palindrome(word: str) -> bool:
    cleaned = word.lower().replace(" ", "")
    return cleaned == cleaned[::-1]
