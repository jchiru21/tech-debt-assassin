"""Simple math utilities — no type hints anywhere."""


def add(a: float, b: float) -> float:
    return a + b


def multiply(x: float, y: float) -> float:
    return x * y


def divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        raise ValueError("Cannot divide by zero")
    return numerator / denominator


def factorial(n: int) -> int:
    if n < 0:
        raise ValueError("Negative numbers not allowed")
    if n <= 1:
        return 1
    return n * factorial(n - 1)
