from __future__ import annotations

import os
from typing import Any
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://wdzkeszoaziixorgnfuw.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indkemtlc3pvYXppaXhvcmduZnV3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk0NjQ0MDYsImV4cCI6MjA4NTA0MDQwNn0.VoPrVh-QKC3drGYzJMshzBJyd-a5sWDkmtmBNAwhOi8")

client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def initialize() -> None:
    pass

def get_auctions() -> list[dict[str, Any]]:
    response = client.table('auctions').select('*').order('created_at', desc=True).execute()
    return response.data

def get_auction(auction_id: str) -> dict[str, Any] | None:
    response = client.table('auctions').select('*').eq('id', auction_id).execute()
    return response.data[0] if response.data else None

def create_auction(auction: dict[str, Any]) -> dict[str, Any]:
    response = client.table('auctions').insert({
        "id": auction["id"],
        "name": auction["name"],
        "location": auction["location"],
        "status": auction["status"],
        "youtube_url": auction.get("youtube_url", ""),
        "whatsapp_number": auction.get("whatsapp_number", ""),
        "created_at": auction["created_at"]
    }).execute()
    return response.data[0] if response.data else auction

def update_auction(auction_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    response = client.table('auctions').update(updates).eq('id', auction_id).execute()
    return response.data[0] if response.data else None

def get_readings(auction_id: str, limit: int = 50) -> list[dict[str, Any]]:
    response = client.table('readings').select('*').eq('auction_id', auction_id).order('id', desc=True).limit(limit).execute()
    return response.data

def get_reading(reading_id: int) -> dict[str, Any] | None:
    response = client.table('readings').select('*').eq('id', reading_id).execute()
    return response.data[0] if response.data else None

def create_reading(reading: dict[str, Any]) -> dict[str, Any]:
    record = {
        "auction_id": reading["auction_id"],
        "captured_at": reading["captured_at"],
        "lot": reading.get("lot"),
        "price_cents": reading.get("price_cents"),
        "description": reading.get("description", ""),
        "confidence": reading.get("confidence"),
        "image_url": reading.get("image_url"),
        "payload": reading
    }
    try:
        response = client.table('readings').insert(record).execute()
        return response.data[0] if response.data else reading
    except Exception as e:
        print("Insert reading info:", e)
        return reading

def create_correction(correction: dict[str, Any]) -> dict[str, Any]:
    response = client.table('corrections').insert(correction).execute()
    return response.data[0] if response.data else correction

def create_alert(alert_data: dict[str, Any]) -> dict[str, Any]:
    try:
        response = client.table('alerts').insert({
            "auction_id": alert_data.get("auction_id"),
            "phone": alert_data.get("phone"),
            "keywords": alert_data.get("keywords", []),
            "max_price_cents": alert_data.get("max_price_cents")
        }).execute()
        return response.data[0] if response.data else alert_data
    except Exception as e:
        print("Alert storage info:", e)
        return alert_data

def clear_readings_for_auction(auction_id: str) -> int:
    try:
        response = client.table('readings').delete().eq('auction_id', auction_id).execute()
        return len(response.data) if response.data else 0
    except Exception as e:
        print("Clear readings info:", e)
        return 0

def get_storage_stats() -> dict[str, Any]:
    try:
        response = client.table('readings').select('id', count='exact').execute()
        count = response.count if response.count is not None else (len(response.data) if response.data else 0)
        estimated_mb = round((count * 1.2) / 1024, 2)
        return {"total_readings": count, "estimated_mb": estimated_mb}
    except Exception as e:
        return {"total_readings": 0, "estimated_mb": 0.0, "error": str(e)}
