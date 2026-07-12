"""Generate README preview collages from aesthepdf_output sample PDFs."""

from __future__ import annotations

import fitz
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "images"
PDF_DIR = ROOT / "aesthepdf_output"

THEMES = [
    ("proposal", "方案建议书", 0, 2),
    ("academic", "学术报告", 0, 2),
    ("whitepaper", "白皮书", 0, 3),
    ("brief", "执行简报", 0, 2),
    ("manual", "产品手册", 0, 3),
]

MATRIX = fitz.Matrix(3.0, 3.0)
GAP = 24
PAD = 32
BG = (245, 244, 240)
LABEL_H = 52
FONT_SIZE = 28
ROW_TARGET_H = 1000
OVERVIEW_COL_W = 520
OVERVIEW_PAGE_H = 720


def render_page(pdf_path: Path, page_idx: int) -> Image.Image:
    doc = fitz.open(pdf_path)
    page = doc[page_idx]
    pix = page.get_pixmap(matrix=MATRIX, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return img


def resize_to_height(img: Image.Image, height: int) -> Image.Image:
    width = int(img.width * height / img.height)
    return img.resize((width, height), Image.LANCZOS)


def try_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("msyh.ttc", "msyhbd.ttc", "arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def make_row(
    images: list[Image.Image],
    labels: list[str],
    target_h: int,
    filename: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    resized = [resize_to_height(im, target_h) for im in images]
    row_w = sum(im.width for im in resized) + GAP * (len(resized) - 1)
    canvas_h = PAD * 2 + target_h + LABEL_H
    canvas = Image.new("RGB", (row_w + PAD * 2, canvas_h), BG)
    draw = ImageDraw.Draw(canvas)
    x = PAD
    for im, label in zip(resized, labels):
        canvas.paste(im, (x, PAD))
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(
            (x + (im.width - tw) // 2, PAD + target_h + 8),
            label,
            fill=(60, 60, 60),
            font=font,
        )
        x += im.width + GAP
    out_path = OUT / filename
    canvas.save(out_path, format="PNG")
    print(f"wrote {out_path} ({canvas.width}x{canvas.height})")


def make_overview(
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    pair_w = OVERVIEW_COL_W
    pair_h_cover = OVERVIEW_PAGE_H
    pair_h_content = OVERVIEW_PAGE_H
    cols = len(THEMES)
    canvas_w = PAD * 2 + cols * pair_w + GAP * (cols - 1)
    canvas_h = PAD * 2 + pair_h_cover + 8 + pair_h_content + LABEL_H
    canvas = Image.new("RGB", (canvas_w, canvas_h), BG)
    draw = ImageDraw.Draw(canvas)
    for i, (tid, name, cover_page, content_page) in enumerate(THEMES):
        x = PAD + i * (pair_w + GAP)
        cover = resize_to_height(
            render_page(PDF_DIR / f"{tid}.pdf", cover_page), pair_h_cover
        )
        content = resize_to_height(
            render_page(PDF_DIR / f"{tid}.pdf", content_page), pair_h_content
        )
        canvas.paste(cover, (x + (pair_w - cover.width) // 2, PAD))
        canvas.paste(
            content,
            (x + (pair_w - content.width) // 2, PAD + pair_h_cover + 8),
        )
        bbox = draw.textbbox((0, 0), name, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(
            (
                x + (pair_w - tw) // 2,
                PAD + pair_h_cover + 8 + pair_h_content + 8,
            ),
            name,
            fill=(60, 60, 60),
            font=font,
        )
    out_path = OUT / "themes-overview.png"
    canvas.save(out_path, format="PNG")
    print(f"wrote {out_path} ({canvas.width}x{canvas.height})")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    font = try_font(FONT_SIZE)

    covers, labels = [], []
    for tid, name, cover_page, _ in THEMES:
        covers.append(render_page(PDF_DIR / f"{tid}.pdf", cover_page))
        labels.append(name)
    make_row(covers, labels, ROW_TARGET_H, "covers.png", font)

    contents, content_labels = [], []
    for tid, name, _, content_page in THEMES:
        contents.append(render_page(PDF_DIR / f"{tid}.pdf", content_page))
        content_labels.append(name)
    make_row(contents, content_labels, ROW_TARGET_H, "samples.png", font)

    make_overview(font)


if __name__ == "__main__":
    main()
