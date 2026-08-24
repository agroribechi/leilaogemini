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
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    image_url: str | None = None


class AlertInput(BaseModel):
    auction_id: str
    phone: str
    keywords: list[str] = Field(default_factory=list)
    max_price_cents: int | None = None
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


@app.get("/api/auctions/active")
def get_active_auction() -> dict[str, Any]:
    auctions = database.get_auctions()
    live = next((a for a in auctions if a.get("status") == "live"), None)
    if live:
        return live
    if auctions:
        return auctions[0]
    return {
        "id": "remate-elite-nelore-2026",
        "name": "Remate Elite Nelore",
        "location": "Uberaba · MG",
        "status": "live",
        "youtube_url": "https://www.youtube.com/watch?v=yG9urdYMH6w&t=2714s"
    }


@app.get("/api/auctions/{auction_id}")
def get_auction(auction_id: str) -> dict[str, Any]:
    if auction_id == "active":
        return get_active_auction()
    auction = database.get_auction(auction_id)
    if not auction:
        raise HTTPException(status_code=404, detail="Leilão não encontrado")
    return auction


@app.get("/api/auctions/{auction_id}/latest")
def get_latest_reading(auction_id: str) -> dict[str, Any]:
    target_id = auction_id
    if auction_id == "active":
        active = get_active_auction()
        target_id = active.get("id", "auction-demo")
    readings = database.get_readings(target_id, limit=1)
    if readings:
        return readings[0]
    return {
        "auction_id": target_id,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "lot": 47,
        "price_cents": 1850000,
        "description": "20 novilhas Nelore prenhes"
    }


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
    target_id = auction_id
    if auction_id == "active":
        active = get_active_auction()
        target_id = active.get("id", "remate-elite-nelore-2026")
    readings = database.get_readings(target_id, min(limit, 500))
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


@app.post("/api/alerts", status_code=201)
async def create_alert(payload: AlertInput) -> dict[str, Any]:
    alert = database.create_alert(payload.model_dump())
    return {"status": "success", "message": f"Alerta registrado para {payload.phone}", "data": alert}


@app.get("/api/system/storage-stats")
def get_storage_stats() -> dict[str, Any]:
    return database.get_storage_stats()


@app.delete("/api/auctions/{auction_id}/clear-readings")
def clear_auction_readings(auction_id: str) -> dict[str, Any]:
    deleted_count = database.clear_readings_for_auction(auction_id)
    return {"status": "success", "message": f"Removidas {deleted_count} leituras do leilão {auction_id}", "deleted_count": deleted_count}


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


class CustomerInput(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: str
    document_cpf: str
    phone: str = ""
    password_hash: str

class CustomerPaymentInput(BaseModel):
    amount_cents: int = Field(ge=0)
    status: str = "pending"
    description: str = ""

class CustomerAccessInput(BaseModel):
    auction_id: str

@app.get("/api/customers")
def list_customers() -> list[dict[str, Any]]:
    return database.get_customers()

@app.post("/api/customers", status_code=201)
def add_customer(payload: CustomerInput) -> dict[str, Any]:
    return database.create_customer(payload.model_dump())

@app.get("/api/customers/{customer_id}")
def get_customer_details(customer_id: str) -> dict[str, Any]:
    customer = database.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    customer["payments"] = database.get_customer_payments(customer_id)
    customer["accesses"] = database.get_customer_accesses(customer_id)
    return customer

@app.post("/api/customers/{customer_id}/payments", status_code=201)
def add_customer_payment(customer_id: str, payload: CustomerPaymentInput) -> dict[str, Any]:
    data = payload.model_dump()
    data["customer_id"] = customer_id
    return database.create_customer_payment(data)

@app.post("/api/customers/{customer_id}/access", status_code=201)
def add_customer_access(customer_id: str, payload: CustomerAccessInput) -> dict[str, Any]:
    data = payload.model_dump()
    data["customer_id"] = customer_id
    return database.create_customer_access(data)

@app.delete("/api/customers/{customer_id}/access/{auction_id}")
def remove_customer_access(customer_id: str, auction_id: str) -> dict[str, Any]:
    if database.remove_customer_access(customer_id, auction_id):
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="Erro ao remover acesso")

@app.websocket("/ws/auctions/{auction_id}")
async def auction_events(websocket: WebSocket, auction_id: str) -> None:
    await manager.connect(auction_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(auction_id, websocket)
