"""Input validators — missing every hint."""

import re


def is_valid_email(email):
    pattern = r"^[\w\.\+\-]+@[\w\-]+\.[\w\.\-]+$"
    return bool(re.match(pattern, email))


def is_strong_password(password):
    if len(password) < 8:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_upper and has_lower and has_digit


def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))


def is_positive_int(value):
    return isinstance(value, int) and value > 0
