import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Adiciona o leilao_ocr ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from leilao_ocr.ocr import TesseractReader
from leilao_ocr.normalization import normalize_lot, normalize_price_cents, normalize_description

def test_ocr():
    reader = TesseractReader(r"C:\Program Files\Tesseract-OCR\tesseract.exe")

    # 1. Simula imagem de Lote
    img_lote = Image.new('RGB', (200, 60), color=(20, 20, 20))
    draw = ImageDraw.Draw(img_lote)
    # Tenta usar fonte padrão ou básica
    draw.text((20, 15), "LOTE 047", fill=(255, 255, 255))
    raw_lote = reader.read(img_lote, "lot")
    norm_lote = normalize_lot(raw_lote)

    # 2. Simula imagem de Preço
    img_preco = Image.new('RGB', (250, 60), color=(20, 20, 20))
    draw = ImageDraw.Draw(img_preco)
    draw.text((20, 15), "R$ 18.500,00", fill=(255, 255, 255))
    raw_preco = reader.read(img_preco, "price")
    norm_preco = normalize_price_cents(raw_preco)

    # 3. Simula imagem de Descrição
    img_desc = Image.new('RGB', (450, 60), color=(20, 20, 20))
    draw = ImageDraw.Draw(img_desc)
    draw.text((20, 15), "20 novilhas Nelore prenhes", fill=(255, 255, 255))
    raw_desc = reader.read(img_desc, "description")
    norm_desc = normalize_description(raw_desc)

    print("=== RESULTADO DO TESTE DE OCR SINTÉTICO ===")
    print(f"[Lote]       Raw: '{raw_lote}' -> Normalizado: {norm_lote}")
    print(f"[Preço]      Raw: '{raw_preco}' -> Normalizado (centavos): {norm_preco} (R$ {norm_preco/100:.2f} se válido)")
    print(f"[Descrição]  Raw: '{raw_desc}' -> Normalizado: '{norm_desc}'")
    print("===========================================")

if __name__ == "__main__":
    test_ocr()
