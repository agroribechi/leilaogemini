from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4


DEFAULT_AUCTIONS = [
    {
        "id": "remate-elite-nelore-2026",
        "name": "Remate Elite Nelore — Genética & Seleção 2026",
        "location": "Uberaba, MG",
        "status": "ready",
    }
]


class AuctionStore:
    """Catálogo local de leilões disponíveis para a operação de captura."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[dict[str, str]]:
        if not self.path.exists():
            self.save(DEFAULT_AUCTIONS)
        return json.loads(self.path.read_text(encoding="utf-8")).get("auctions", [])

    def save(self, auctions: list[dict[str, str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"auctions": auctions}, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, name: str, location: str, auction_id: str | None = None) -> dict[str, str]:
        auctions = self.load()
        aid = auction_id or f"auction-{uuid4().hex[:10]}"
        auction = {"id": aid, "name": name.strip(), "location": location.strip(), "status": "ready"}
        auctions.append(auction)
        self.save(auctions)
        return auction


class OperationStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load_selected_id(self) -> str | None:
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text(encoding="utf-8")).get("selected_auction_id")

    def save_selected_id(self, auction_id: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"selected_auction_id": auction_id}, ensure_ascii=False, indent=2), encoding="utf-8")
