"""Gera ícone placeholder para o aplicativo desktop."""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit("Pillow necessário: pip install Pillow")

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "desktop" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

png_path = ASSETS / "icon.png"
ico_path = ASSETS / "icon.ico"

size = 256
img = Image.new("RGBA", (size, size), (15, 76, 92, 255))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle((24, 24, 232, 232), radius=32, fill=(27, 107, 122, 255))
draw.text((72, 108), "OAE", fill=(255, 255, 255, 255))

img.save(png_path)
img.save(ico_path, sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])

print(f"Ícones gerados: {png_path} e {ico_path}")
