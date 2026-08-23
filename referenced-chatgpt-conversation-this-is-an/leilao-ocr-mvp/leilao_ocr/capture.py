from __future__ import annotations

import mss
from PIL import Image

from .models import Region


class ScreenCapture:
    """Captura a tela virtual; as regiões usam coordenadas absolutas da tela."""

    def bounds(self) -> Region:
        with mss.mss() as screen:
            monitor = screen.monitors[0]
            return Region(monitor["left"], monitor["top"], monitor["width"], monitor["height"])

    def grab(self, region: Region | None = None) -> Image.Image:
        with mss.mss() as screen:
            monitor = {"left": region.left, "top": region.top, "width": region.width, "height": region.height} if region else screen.monitors[0]
            shot = screen.grab(monitor)
            return Image.frombytes("RGB", shot.size, shot.rgb)
