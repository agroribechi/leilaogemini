from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import database

app = FastAPI(title="Arremate API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class AuctionInput(BaseModel):
    name: str = Field(min_length=3, max_length=140)
    location: str = Field(min_length=2, max_length=100)
    youtube_url: str = ""
    whatsapp_number: str = ""


class AuctionUpdateInput(BaseModel):
    name: str | None = None
    location: str | None = None
    status: str | None = None
    youtube_url: str | None = None
    whatsapp_number: str | None = None


class ReadingInput(BaseModel):
    auction_id: str
    auction_name: str | None = None
    captured_at: str
    lot: int | None = Field(default=None, ge=0)
    price_cents: int | None = Field(default=None, ge=0)
    description: str | None = None
    raw_lot: str = ""
    raw_price: str = ""
    raw_description: str = ""
    confidence: float | None = Field(default=None, ge=0, le=100)


class CorrectionInput(BaseModel):
    lot: int | None = Field(default=None, ge=0)
    price_cents: int | None = Field(default=None, ge=0)
    description: str | None = None


class ConnectionManager:
    def __init__(self) -> None:
        self.clients: dict[str, list[WebSocket]] = {}

    async def connect(self, auction_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.clients.setdefault(auction_id, []).append(websocket)

    def disconnect(self, auction_id: str, websocket: WebSocket) -> None:
        if websocket in self.clients.get(auction_id, []):
            self.clients[auction_id].remove(websocket)

    async def broadcast(self, auction_id: str, event: dict[str, Any]) -> None:
        for websocket in self.clients.get(auction_id, []).copy():
            try:
                await websocket.send_json(event)
            except Exception:
                self.disconnect(auction_id, websocket)


manager = ConnectionManager()


@app.on_event("startup")
def startup() -> None:
    database.initialize()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/auctions")
def list_auctions() -> list[dict[str, Any]]:
    return database.get_auctions()


@app.post("/api/auctions", status_code=201)
def add_auction(payload: AuctionInput) -> dict[str, Any]:
    auction = {
        "id": f"auction-{uuid4().hex[:10]}",
        "name": payload.name,
        "location": payload.location,
        "youtube_url": payload.youtube_url,
        "whatsapp_number": getattr(payload, 'whatsapp_number', ''),
        "status": "scheduled",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return database.create_auction(auction)


@app.patch("/api/auctions/{auction_id}")
async def update_auction_details(auction_id: str, payload: AuctionUpdateInput) -> dict[str, Any]:
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = database.update_auction(auction_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Leilão não encontrado")
    event = {"type": "auction.updated", "data": updated}
    await manager.broadcast(auction_id, event)
    return event


@app.post("/api/readings", status_code=201)
async def add_reading(payload: ReadingInput) -> dict[str, Any]:
    if not database.get_auction(payload.auction_id):
        raise HTTPException(status_code=404, detail="Leilão não encontrado")
    reading = database.create_reading(payload.model_dump())
    event = {"type": "reading.created", "data": reading}
    await manager.broadcast(payload.auction_id, event)
    return event


@app.get("/api/auctions/{auction_id}/readings")
def list_readings(auction_id: str, limit: int = 50, distinct_by_lot: bool = True) -> list[dict[str, Any]]:
    readings = database.get_readings(auction_id, min(limit, 500))
    if distinct_by_lot:
        seen_lots: set[Any] = set()
        unique_readings: list[dict[str, Any]] = []
        for r in readings:
            lot = r.get("lot")
            if lot is not None:
                if lot not in seen_lots:
                    seen_lots.add(lot)
                    unique_readings.append(r)
            else:
                unique_readings.append(r)
        return unique_readings
    return readings


@app.post("/api/readings/{reading_id}/corrections", status_code=201)
async def correct_reading(reading_id: int, payload: CorrectionInput) -> dict[str, Any]:
    reading = database.get_reading(reading_id)
    if not reading:
        raise HTTPException(status_code=404, detail="Leitura não encontrada")
    corrected_at = datetime.now(timezone.utc).isoformat()
    
    database.create_correction({
        "reading_id": reading_id,
        "lot": payload.lot,
        "price_cents": payload.price_cents,
        "description": payload.description,
        "corrected_at": corrected_at
    })
    
    event = {"type": "reading.corrected", "data": {"id": reading_id, "auction_id": reading["auction_id"], **payload.model_dump(), "corrected_at": corrected_at}}
    await manager.broadcast(reading["auction_id"], event)
    return event


@app.websocket("/ws/auctions/{auction_id}")
async def auction_events(websocket: WebSocket, auction_id: str) -> None:
    await manager.connect(auction_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(auction_id, websocket)
