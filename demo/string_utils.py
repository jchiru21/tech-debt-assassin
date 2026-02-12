"""String manipulation helpers — completely untyped."""


def reverse_string(s):
    return s[::-1]


def count_vowels(text):
    return sum(1 for ch in text.lower() if ch in "aeiou")


def truncate(text, max_length, suffix="..."):
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def is_palindrome(word):
    cleaned = word.lower().replace(" ", "")
    return cleaned == cleaned[::-1]
