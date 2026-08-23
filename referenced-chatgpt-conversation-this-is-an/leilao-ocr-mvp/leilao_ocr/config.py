from __future__ import annotations

import json
from pathlib import Path

from .models import Region

REGION_NAMES = ("video", "lot", "price", "description")


class ConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Region]:
        if not self.path.exists():
            return {}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return {name: Region.from_dict(value) for name, value in raw.get("regions", {}).items()}

    def save(self, regions: dict[str, Region]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = {"version": 1, "regions": {name: region.as_dict() for name, region in regions.items()}}
        self.path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")

