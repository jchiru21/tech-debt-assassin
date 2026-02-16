# messy_code.py
def calculate_total(price: float, tax: float) -> float:
    # This function has NO type hints (Bad!)
    return price + (price * tax)

def greet_user(name: str) -> str:
    # This function HAS type hints (Good!)
    return f"Hello, {name}"