import os
from google import genai
from pydantic import BaseModel
import threading
import logging

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

class OcrResult(BaseModel):
    lot: int | None
    price_cents: int | None
    description: str | None

def refine_with_gemini(raw_lot: str, raw_price: str, raw_desc: str) -> OcrResult | None:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""Você é um sistema de IA limpando dados de OCR de um leilão de gado ao vivo no Brasil.
        Texto bruto do Lote: "{raw_lot}"
        Texto bruto do Preço: "{raw_price}"
        Texto bruto da Descrição: "{raw_desc}"
        
        Sua tarefa:
        1. 'lot': Extrair apenas o número inteiro do lote (remova palavras como "lote"). Retorne null se não houver número.
        2. 'price_cents': Extrair o preço total em CENTAVOS de real. Por exemplo, se ler R$ 18.500,00, retorne 1850000. Retorne null se não conseguir identificar o valor numérico.
        3. 'description': Corrigir pequenos erros de digitação (OCR) em nomes de fazendas, raças de gado e descrições do lote, retornando um texto limpo e legível. Retorne null se estiver muito quebrado.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': OcrResult,
            },
        )
        return response.parsed
    except Exception as e:
        logging.error(f"Gemini error: {e}")
        return None
