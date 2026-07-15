"""Generate README preview collage from aesthepdf_output sample PDFs."""

from __future__ import annotations

import fitz
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "images"
PDF_DIR = ROOT / "aesthepdf_output"

# 3 rows × 5 cols — one column per theme: cover + two inner pages
THEMES: list[tuple[str, str, int, int, int]] = [
    ("proposal", "方案建议书", 0, 2, 4),
    ("academic", "学术报告", 0, 2, 5),
    ("whitepaper", "白皮书", 0, 3, 5),
    ("brief", "执行简报", 0, 2, 4),
    ("manual", "产品手册", 0, 2, 3),
]

MATRIX = fitz.Matrix(3.0, 3.0)
GAP = 18
PAD = 24
BG = (245, 244, 240)
CELL_W = 520
CELL_H = 780
LABEL_H = 38
FONT_SIZE = 22


def render_page(pdf_path: Path, page_idx: int) -> Image.Image:
    doc = fitz.open(pdf_path)
    if page_idx >= len(doc):
        raise ValueError(f"{pdf_path.name} has {len(doc)} pages, need index {page_idx}")
    page = doc[page_idx]
    pix = page.get_pixmap(matrix=MATRIX, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return img


def fit_to_cell(img: Image.Image, cell_w: int, cell_h: int) -> Image.Image:
    scale = min(cell_w / img.width, cell_h / img.height)
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    cell = Image.new("RGB", (cell_w, cell_h), BG)
    cell.paste(resized, ((cell_w - new_w) // 2, (cell_h - new_h) // 2))
    return cell


def try_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("msyh.ttc", "msyhbd.ttc", "arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def make_grid(
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    filename: str = "preview-grid.png",
) -> None:
    cols = len(THEMES)
    rows = 3

    canvas_w = PAD * 2 + cols * CELL_W + GAP * (cols - 1)
    canvas_h = PAD * 2 + rows * (CELL_H + LABEL_H) + GAP * (rows - 1)
    canvas = Image.new("RGB", (canvas_w, canvas_h), BG)
    draw = ImageDraw.Draw(canvas)

    for col_idx, (theme_id, label, cover_p, inner1_p, inner2_p) in enumerate(THEMES):
        x = PAD + col_idx * (CELL_W + GAP)
        pages = [cover_p, inner1_p, inner2_p]
        for row_idx, page_idx in enumerate(pages):
            y = PAD + row_idx * (CELL_H + LABEL_H + GAP)
            img = render_page(PDF_DIR / f"{theme_id}.pdf", page_idx)
            cell = fit_to_cell(img, CELL_W, CELL_H)
            canvas.paste(cell, (x, y))
            if row_idx == 0:
                bbox = draw.textbbox((0, 0), label, font=font)
                tw = bbox[2] - bbox[0]
                draw.text(
                    (x + (CELL_W - tw) // 2, y + CELL_H + 6),
                    label,
                    fill=(60, 60, 60),
                    font=font,
                )

    out_path = OUT / filename
    canvas.save(out_path, format="PNG")
    print(f"wrote {out_path} ({canvas.width}x{canvas.height})")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    make_grid(try_font(FONT_SIZE))


if __name__ == "__main__":
    main()
