"""API helper utilities — riddled with missing and broken type hints."""

import json
import time
from datetime import datetime


# 1. Completely untyped — no hints at all
def build_url(base: str, endpoint: str, params: dict[str, str | int | float]) -> str:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{base}/{endpoint}?{query}" if params else f"{base}/{endpoint}"


# 2. Missing return type only
def parse_json_response(raw: str) -> dict | list | str | int | float | bool | None:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


# 3. Missing param hints, return type present
def retry_request(func: callable, max_retries: int, delay: float) -> bool:
    for attempt in range(max_retries):
        try:
            func()
            return True
        except Exception:
            time.sleep(delay)
    return False


# 4. Typo in annotation — scanner catches invalid type names
def format_timestamp(ts: float) -> str:
    return datetime.fromtimestamp(ts).isoformat()


# 5. Partial hints — some params typed, others not
def paginate(items: list, page: int, page_size: int) -> list:
    start = (page - 1) * page_size
    return items[start : start + page_size]


# 6. Method inside a class — self/cls should be skipped
class ApiClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url
        self.timeout = timeout

    def get(self, endpoint: str, headers: dict[str, str]) -> dict[str, str | dict[str, str]]:
        return {"url": f"{self.base_url}/{endpoint}", "headers": headers}

    def post(self, endpoint: str, payload: dict[str, object], headers: dict[str, str]) -> dict[str, object]:
        return {"url": f"{self.base_url}/{endpoint}", "body": payload}


# 7. Async function — completely untyped
async def fetch_data(url: str, session: 'aiohttp.ClientSession') -> dict | list | None:
    async with session.get(url) as resp:
        return await resp.json()


# 8. One good function (fully typed) — proves health isn't always 0%
def status_code_ok(code: int) -> bool:
    return 200 <= code < 300
