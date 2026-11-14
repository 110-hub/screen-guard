# -*- coding: utf-8 -*-
"""生成程序图标 assets/icon.ico（蓝底 + 书本 + 字母 A）。"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets")
os.makedirs(OUT_DIR, exist_ok=True)


def draw(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = int(size * 0.06)
    radius = int(size * 0.2)
    d.rounded_rectangle([pad, pad, size - pad, size - pad], radius=radius,
                        fill=(37, 55, 100, 255), outline=(79, 124, 255, 255),
                        width=max(1, int(size * 0.03)))
    font = None
    for name in ("arialbd.ttf", "segoeuib.ttf", "arial.ttf"):
        try:
            font = ImageFont.truetype(name, int(size * 0.52))
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    d.text((size / 2, size * 0.46), "A", font=font, fill=(255, 255, 255, 255), anchor="mm")
    # 底部三条小书页
    bar_w = int(size * 0.5)
    x0 = (size - bar_w) / 2
    for i, w in enumerate((1.0, 0.82, 0.64)):
        y = size * 0.78 + i * size * 0.055
        d.rounded_rectangle([x0, y, x0 + bar_w * w, y + size * 0.035],
                            radius=size * 0.018, fill=(79, 124, 255, 235))
    return img


sizes = [16, 24, 32, 48, 64, 128, 256]
images = [draw(s) for s in sizes]
out = os.path.join(OUT_DIR, "icon.ico")
images[-1].save(out, format="ICO", sizes=[(s, s) for s in sizes])
images[-1].save(os.path.join(OUT_DIR, "icon.png"), format="PNG")
print("saved:", out, os.path.getsize(out), "bytes")
