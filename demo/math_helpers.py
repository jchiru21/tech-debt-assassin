"""Simple math utilities — no type hints anywhere."""


def add(a, b):
    return a + b


def multiply(x, y):
    return x * y


def divide(numerator, denominator):
    if denominator == 0:
        raise ValueError("Cannot divide by zero")
    return numerator / denominator


def factorial(n):
    if n < 0:
        raise ValueError("Negative numbers not allowed")
    if n <= 1:
        return 1
    return n * factorial(n - 1)
