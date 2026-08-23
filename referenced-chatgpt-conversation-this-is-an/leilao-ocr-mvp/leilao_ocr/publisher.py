from __future__ import annotations

import json
import os
from typing import Protocol
from urllib.request import Request, urlopen

from .models import Reading


class ReadingPublisher(Protocol):
    def publish(self, reading: Reading) -> None: ...


class NullPublisher:
    """Ponto de extensão: substituir por cliente HTTP (FastAPI) ou Supabase."""
    def publish(self, reading: Reading) -> None:
        return None


class HttpPublisher:
    """Envia a leitura para a FastAPI; não exige bibliotecas adicionais."""

    def __init__(self, base_url: str) -> None:
        self.url = base_url.rstrip("/") + "/api/readings"

    def publish(self, reading: Reading) -> None:
        payload = json.dumps(reading.as_dict(), ensure_ascii=False).encode("utf-8")
        request = Request(self.url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=5) as response:
                if response.status >= 300:
                    raise RuntimeError(f"API retornou HTTP {response.status}")
        except Exception as e:
            if "ConnectionRefused" in str(e) or "WinError 10061" in str(e):
                raise RuntimeError("API local desligada ou inacessível (127.0.0.1:8000)") from e
            raise


def publisher_from_environment() -> ReadingPublisher:
    base_url = os.getenv("LEILAO_API_URL", "http://127.0.0.1:8000")
    return HttpPublisher(base_url) if base_url else NullPublisher()

