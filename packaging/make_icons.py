"""Genera los iconos de Myna (.ico para Windows + PNGs) a partir del SVG del tile.

Uso:  .venv\\Scripts\\python.exe packaging\\make_icons.py
Requiere (solo dev):  pip install svglib reportlab pillow
Produce:
  - myna.ico                         (raíz; atajo de Windows + instalador)
  - frontend/public/favicon.ico      (pestaña del navegador, formato clásico)
  - frontend/public/apple-touch-icon.png  (iOS / PWA, 180x180)
"""
import os

from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TILE_SVG = os.path.join(ROOT, "frontend", "public", "myna_app_tile.svg")
RADIUS_RATIO = 115 / 512   # rx del SVG respecto al lado


def render_tile(size):
    """Rasteriza el SVG del tile a un PIL.Image RGBA con esquinas redondeadas."""
    drawing = svg2rlg(TILE_SVG)
    scale = size / drawing.width
    drawing.width *= scale
    drawing.height *= scale
    drawing.scale(scale, scale)
    img = renderPM.drawToPIL(drawing, bg=0xFFFFFF).convert("RGBA")

    # Recorta las esquinas (quedan blancas del fondo de página) con una máscara redondeada.
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=int(size * RADIUS_RATIO), fill=255)
    img.putalpha(mask)
    return img


def main():
    base = render_tile(1024)  # render grande y luego se reescala para nitidez
    sizes = [16, 32, 48, 64, 128, 256]
    icons = [base.resize((s, s), Image.LANCZOS) for s in sizes]

    ico_root = os.path.join(ROOT, "myna.ico")
    icons[-1].save(ico_root, format="ICO", sizes=[(s, s) for s in sizes])
    print("ok:", ico_root)

    fav = os.path.join(ROOT, "frontend", "public", "favicon.ico")
    icons[-1].save(fav, format="ICO", sizes=[(s, s) for s in sizes])
    print("ok:", fav)

    apple = os.path.join(ROOT, "frontend", "public", "apple-touch-icon.png")
    base.resize((180, 180), Image.LANCZOS).save(apple)
    print("ok:", apple)


if __name__ == "__main__":
    main()
