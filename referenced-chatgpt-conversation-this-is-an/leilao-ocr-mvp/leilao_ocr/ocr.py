from __future__ import annotations

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def preprocess(image: Image.Image, scale: int = 3) -> Image.Image:
    gray = ImageOps.grayscale(image)
    enlarged = gray.resize((gray.width * scale, gray.height * scale))
    enhanced = ImageEnhance.Contrast(enlarged).enhance(2.2).filter(ImageFilter.SHARPEN)
    return enhanced.point(lambda pixel: 255 if pixel > 155 else 0)


class TesseractReader:
    def __init__(self, executable: str | None = None) -> None:
        if executable:
            pytesseract.pytesseract.tesseract_cmd = executable

    def read(self, image: Image.Image, field: str) -> str:
        config = "--psm 7" if field in {"lot", "price"} else "--psm 6"
        if field == "lot":
            config += " -c tessedit_char_whitelist=0123456789LOTElote:#- "
        elif field == "price":
            config += " -c tessedit_char_whitelist=0123456789R$., "
        return pytesseract.image_to_string(preprocess(image), lang="por", config=config).strip()

