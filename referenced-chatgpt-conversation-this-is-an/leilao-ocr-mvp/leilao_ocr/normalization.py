from __future__ import annotations

import re
import unicodedata


def clean_text(value: str) -> str:
    return " ".join(value.replace("\n", " ").split())


def normalize_lot(value: str) -> int | None:
    match = re.search(r"(?:lote\s*[:#-]?\s*)?(\d{1,6})", value, re.IGNORECASE)
    return int(match.group(1)) if match else None


def normalize_price_cents(value: str) -> int | None:
    text = value.upper().replace("O", "0")
    text = re.sub(r"[^0-9,\.]", "", text)
    if not text:
        return None
    # Em PT-BR, ponto normalmente separa milhares e vírgula separa centavos.
    if "," in text:
        integer, decimals = text.rsplit(",", 1)
        integer = integer.replace(".", "") or "0"
        return int(integer) * 100 + int((decimals + "00")[:2])
    digits = text.replace(".", "")
    return int(digits) * 100 if digits else None


def normalize_description(value: str) -> str:
    text = clean_text(value)
    # Mantém acentos, mas remove caracteres de controle e espaços redundantes.
    return "".join(char for char in text if unicodedata.category(char)[0] != "C")

