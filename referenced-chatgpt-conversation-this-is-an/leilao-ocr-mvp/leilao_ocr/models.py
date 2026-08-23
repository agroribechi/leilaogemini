from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Region:
    left: int
    top: int
    width: int
    height: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Region":
        return cls(**{key: int(value[key]) for key in ("left", "top", "width", "height")})


@dataclass(frozen=True)
class Reading:
    lot: int | None
    price_cents: int | None
    description: str
    raw_lot: str
    raw_price: str
    raw_description: str
    captured_at: str
    auction_id: str | None = None
    auction_name: str | None = None

    @classmethod
    def now(cls, **kwargs: Any) -> "Reading":
        return cls(captured_at=datetime.now(timezone.utc).isoformat(), **kwargs)

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["price_brl"] = None if self.price_cents is None else self.price_cents / 100
        return result
