import unittest

from leilao_ocr.normalization import normalize_lot, normalize_price_cents


class NormalizationTests(unittest.TestCase):
    def test_lot(self) -> None:
        self.assertEqual(normalize_lot("LOTE: 047"), 47)

    def test_brl_price(self) -> None:
        self.assertEqual(normalize_price_cents("R$ 18.500,75"), 1_850_075)

    def test_integer_price(self) -> None:
        self.assertEqual(normalize_price_cents("18500"), 1_850_000)
