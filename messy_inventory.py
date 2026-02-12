# messy_inventory.py
from typing import Any

def process_items(items: list[dict[str, Any]]) -> float:
    # This should be List[Dict[str, Any]] -> float
    total = 0.0
    for item in items:
        if item.get("in_stock", False):
            total += item["price"] * item["quantity"]
    return total

def find_item(items: list[dict], name: str) -> dict | None:
    # This should return Optional[Dict] or Dict | None
    for item in items:
        if item["name"] == name:
            return item
    return None

def format_receipt(total: float, currency: str) -> str:
    # Simple str formatting
    return f"Total due: {currency}{total:.2f}"