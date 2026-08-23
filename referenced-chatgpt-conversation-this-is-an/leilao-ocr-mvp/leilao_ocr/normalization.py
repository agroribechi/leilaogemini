from __future__ import annotations

import re
import unicodedata


def clean_text(value: str) -> str:
    return " ".join(value.replace("\n", " ").split())


def normalize_lot(value: str) -> int | None:
    if not value:
        return None
    # Remove palavras de prefixo comuns (LOTE, LT, #, etc)
    cleaned = re.sub(r'^(?:LOTE|LT|LOT|N[Oº]?|#|:\s*)+', '', value.upper(), flags=re.IGNORECASE).strip()
    
    # Mapeamento de substituição de confusões OCR frequentes em números
    char_map = {'O': '0', 'Q': '0', 'D': '0', 'I': '1', 'L': '1', 'Z': '2', 'S': '5', 'B': '8'}
    temp = ''.join(char_map.get(ch, ch) for ch in cleaned)
    
    match = re.search(r'(\d{1,6})', temp)
    if match:
        return int(match.group(1))
    
    # Segundo fallback: busca qualquer dígito no texto bruto original
    match_fallback = re.search(r'(\d{1,6})', value)
    return int(match_fallback.group(1)) if match_fallback else None


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

