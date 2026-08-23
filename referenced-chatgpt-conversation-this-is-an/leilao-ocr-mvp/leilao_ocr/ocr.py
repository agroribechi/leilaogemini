from __future__ import annotations

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def preprocess(image: Image.Image, scale: int = 3) -> Image.Image:
    gray = ImageOps.grayscale(image)
    enlarged = gray.resize((gray.width * scale, gray.height * scale), Image.Resampling.LANCZOS)
    enhanced = ImageEnhance.Contrast(enlarged).enhance(2.5).filter(ImageFilter.SHARPEN)
    auto = ImageOps.autocontrast(enhanced, cutoff=2)
    return auto.point(lambda pixel: 255 if pixel > 135 else 0)


class TesseractReader:
    def __init__(self, executable: str | None = None) -> None:
        if executable:
            pytesseract.pytesseract.tesseract_cmd = executable

    def read(self, image: Image.Image, field: str) -> str:
        if field == "lot":
            configs = [
                "--psm 7 -c tessedit_char_whitelist=0123456789LOTEloteLt#:- ",
                "--psm 8 -c tessedit_char_whitelist=0123456789LOTEloteLt#:- ",
                "--psm 7",
                "--psm 6",
            ]
            prep_img = preprocess(image)
            inv_img = ImageOps.invert(prep_img)
            
            # Testa imagem pré-processada, invertida e original para encontrar o melhor resultado com dígitos
            for img in [prep_img, inv_img, image]:
                for cfg in configs:
                    res = pytesseract.image_to_string(img, config=cfg).strip()
                    if res and any(c.isdigit() or c.upper() in "OQDISBZ" for c in res):
                        return res
            return pytesseract.image_to_string(prep_img, config=configs[0]).strip()

        if field == "price":
            configs = [
                "--psm 7 -c tessedit_char_whitelist=0123456789R$., ",
                "--psm 6 -c tessedit_char_whitelist=0123456789R$., ",
                "--psm 7",
            ]
            prep_img = preprocess(image)
            inv_img = ImageOps.invert(prep_img)
            for img in [prep_img, inv_img, image]:
                for cfg in configs:
                    res = pytesseract.image_to_string(img, config=cfg).strip()
                    if res and any(c.isdigit() for c in res):
                        return res
            return pytesseract.image_to_string(prep_img, config=configs[0]).strip()

        return pytesseract.image_to_string(preprocess(image), lang="por", config="--psm 6").strip()

