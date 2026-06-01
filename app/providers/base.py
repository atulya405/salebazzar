from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class ProductCandidate:
    source: str
    external_id: str
    category: str
    name: str
    image_url: str
    current_price: float | None
    original_price: float | None
    store_name: str
    product_url: str
    rating: float = 0
    popularity: float = 0


class ProductProvider(Protocol):
    name: str

    async def fetch(self, category: str) -> list[ProductCandidate]: ...


def float_value(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").replace("₹", "").replace("$", "").strip()
    digits = "".join(char for char in text if char.isdigit() or char in ".-")
    try:
        return float(digits)
    except ValueError:
        return None


def first(data: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        if data.get(key) not in (None, ""):
            return data[key]
    return default


def list_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("products", "results", "items", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = list_payload(value)
            if nested:
                return nested
    return []

