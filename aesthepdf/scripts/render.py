#!/usr/bin/env python3
"""AesthePDF render pipeline: Markdown -> Pandoc HTML -> Chromium PDF."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    PdfReader = None
    PdfWriter = None

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSETS = SKILL_ROOT / "assets"
FILTERS_DIR = ASSETS / "filters"
THEMES_DIR = SKILL_ROOT / "themes"
DEFAULT_THEME = "proposal"
DEFAULT_TEMPLATE = ASSETS / "template.html"

DEFAULT_PANDOC = {
    "from_extensions": ["raw_html"],
    "math": None,
    "highlight": None,
}
DEFAULT_FILTERS = ["section.lua"]
DEFAULT_THEME_DEFAULTS = {"toc": True}


def _require_tools() -> None:
    if shutil.which("pandoc") is None:
        raise SystemExit("pandoc not found. Install from https://pandoc.org/")
    if sync_playwright is None:
        raise SystemExit("playwright not installed. Run: pip install -r scripts/requirements.txt")
    if PdfWriter is None:
        raise SystemExit("pypdf not installed. Run: pip install -r scripts/requirements.txt")


def _to_file_url(path: Path) -> str:
    return path.resolve().as_uri()


def _resolve_filter(name: str) -> Path:
    for candidate in (FILTERS_DIR / name, ASSETS / name):
        if candidate.is_file():
            return candidate
    raise SystemExit(f"Lua filter not found: {name}")


def load_theme_config(theme: str) -> dict[str, Any]:
    theme_dir = THEMES_DIR / theme
    css = theme_dir / "style.css"
    if not css.is_file():
        available = [p.name for p in THEMES_DIR.iterdir() if p.is_dir() and (p / "style.css").is_file()]
        raise SystemExit(f"Unknown theme {theme!r}. Available: {', '.join(available) or '(none)'}")

    config: dict[str, Any] = {
        "id": theme,
        "css": css,
        "template": DEFAULT_TEMPLATE,
        "pandoc": dict(DEFAULT_PANDOC),
        "filters": list(DEFAULT_FILTERS),
        "defaults": dict(DEFAULT_THEME_DEFAULTS),
    }

    meta_path = theme_dir / "theme.json"
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        config.update({k: v for k, v in meta.items() if k != "pandoc"})
        if "pandoc" in meta:
            config["pandoc"] = {**DEFAULT_PANDOC, **meta["pandoc"]}
        if "filters" in meta:
            config["filters"] = meta["filters"]
        elif meta.get("pandoc", {}).get("filters"):
            config["filters"] = meta["pandoc"]["filters"]
        if meta.get("template"):
            tpl = theme_dir / meta["template"]
            if tpl.is_file():
                config["template"] = tpl

    return config


def list_themes() -> list[dict]:
    themes: list[dict] = []
    if not THEMES_DIR.is_dir():
        return themes
    for path in sorted(THEMES_DIR.iterdir()):
        if not path.is_dir() or not (path / "style.css").is_file():
            continue
        meta = {"id": path.name, "name": path.name, "scenario": ""}
        meta_path = path / "theme.json"
        if meta_path.is_file():
            meta.update(json.loads(meta_path.read_text(encoding="utf-8")))
        themes.append(meta)
    return themes


def _read_frontmatter(input_md: Path) -> dict[str, str]:
    text = input_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    values: dict[str, str] = {}
    for line in block.splitlines():
        match = re.match(r"^([\w-]+):\s*(.+)$", line.strip())
        if match:
            val = match.group(2).strip().strip('"').strip("'")
            if val.lower() not in ("true", "false"):
                values[match.group(1)] = val
            else:
                values[match.group(1)] = val.lower()
    return values


def read_document_title(input_md: Path) -> str | None:
    meta = _read_frontmatter(input_md)
    for key in ("document-title", "cover-title", "title"):
        if key in meta:
            return meta[key]
    return None


def read_theme(input_md: Path) -> str | None:
    return _read_frontmatter(input_md).get("theme")


def _cover_enabled(input_md: Path, theme_config: dict[str, Any]) -> bool:
    meta = _read_frontmatter(input_md)
    if meta.get("cover") == "false":
        return False
    if meta.get("cover-title"):
        return True
    return theme_config.get("defaults", {}).get("cover", True)


def _resolve_pandoc_options(theme_config: dict[str, Any], input_md: Path) -> dict[str, Any]:
    """Merge theme pandoc defaults with per-document frontmatter overrides."""
    pandoc = dict(theme_config.get("pandoc", DEFAULT_PANDOC))
    meta = _read_frontmatter(input_md)

    if meta.get("code-highlight") == "true":
        pandoc["highlight"] = "breezeDark"
    elif meta.get("syntax-highlighting"):
        pandoc["highlight"] = meta["syntax-highlighting"]

    return pandoc


def run_pandoc(
    input_md: Path,
    output_html: Path,
    *,
    theme_config: dict[str, Any],
    toc: bool,
    theme: str,
    cover: bool,
    pandoc_options: dict[str, Any] | None = None,
) -> None:
    pandoc_opts = pandoc_options or theme_config.get("pandoc", DEFAULT_PANDOC)
    extensions = pandoc_opts.get("from_extensions", ["raw_html"])
    from_fmt = "markdown+" + "+".join(extensions)

    cmd = [
        "pandoc",
        str(input_md),
        f"--from={from_fmt}",
        "--standalone",
        f"--template={theme_config['template']}",
        f"--css={theme_config['css']}",
        f"--metadata=theme:{theme}",
        f"--metadata=cover:{str(cover).lower()}",
        "--metadata=pagetitle:AesthePDF",
        "-o",
        str(output_html),
    ]

    for flt in theme_config.get("filters", DEFAULT_FILTERS):
        cmd.append(f"--lua-filter={_resolve_filter(flt)}")

    math_mode = pandoc_opts.get("math")
    if math_mode == "mathml":
        cmd.append("--mathml")
    elif math_mode == "katex":
        cmd.append("--katex")

    highlight = pandoc_opts.get("highlight")
    if highlight:
        cmd.append(f"--syntax-highlighting={highlight}")

    if toc:
        cmd.extend(["--toc", "--toc-depth=2", "--variable=toc:true"])

    subprocess.run(cmd, check=True)


def _header_template(page_marker: str, *, theme: str | None, enabled: bool) -> str:
    if not enabled:
        return "<span></span>"
    theme_styles = {
        "proposal": ("#9a9892", "serif", "20mm", "0.04em"),
        "academic": ("#64748b", "serif", "22mm", "0.04em"),
        "whitepaper": ("#78716c", "serif", "24mm", "0.04em"),
        "brief": ("#64748b", "Inter,'Source Han Sans SC',sans-serif", "16mm", "0.06em"),
        "manual": ("#64748b", "'Source Sans 3','Source Han Sans SC',sans-serif", "18mm", "0.04em"),
    }
    color, font_family, padding_x, letter_spacing = theme_styles.get(
        theme, theme_styles["proposal"]
    )
    style = (
        f"width:100%;box-sizing:border-box;padding:0 {padding_x};font-size:8px;"
        f"color:{color};text-align:right;font-family:{font_family};"
        f"letter-spacing:{letter_spacing};white-space:nowrap;overflow:hidden;"
        "text-overflow:ellipsis;"
    )
    return f'<div style="{style}">{html.escape(page_marker)}</div>'


def _install_page_marker_probes(page: Any) -> list[dict[str, Any]]:
    """Attach extractable, visually transparent tokens to running-header sources."""
    return page.evaluate(
        """() => {
          const entries = [...document.querySelectorAll('.document-body h2.section-header')]
            .map((source) => ({
              source,
              text: source.getAttribute('page-header')
                || source.getAttribute('data-page-header')
                || source.textContent.trim(),
              carry: true,
            }));

          const abstractTitle = document.querySelector('.document-body .abstract-title');
          if (abstractTitle) {
            entries.push({
              source: abstractTitle,
              text: abstractTitle.textContent.trim(),
              carry: true,
            });
          }

          const tocTitle = document.querySelector('.toc-page > h1');
          if (tocTitle) {
            entries.push({
              source: tocTitle,
              text: tocTitle.textContent.trim(),
              carry: false,
            });
          }

          entries.sort((a, b) => {
            if (a.source === b.source) return 0;
            return a.source.compareDocumentPosition(b.source) & Node.DOCUMENT_POSITION_FOLLOWING
              ? -1
              : 1;
          });

          return entries.map((entry, index) => {
            const token = `AESTHEPDFMARKER${String(index).padStart(4, '0')}`;
            let target = entry.source;
            const isClippedTocSource = target.matches([
              '.academic-toc-source',
              '.manual-toc-source',
              '.wp-toc-source',
              '.brief-toc-source',
            ].join(','));
            if (getComputedStyle(target).display === 'none' || isClippedTocSource) {
              let sibling = target.nextElementSibling;
              while (sibling && getComputedStyle(sibling).display === 'none') {
                sibling = sibling.nextElementSibling;
              }
              target = sibling || target.parentElement;
            }

            const probe = document.createElement('span');
            probe.className = 'aesthepdf-page-marker-probe';
            probe.textContent = token;
            probe.style.cssText = [
              'position:absolute',
              'top:0',
              'left:0',
              'font:1px Arial,sans-serif',
              'line-height:1',
              'color:rgba(0,0,0,0.01)',
              'white-space:nowrap',
            ].join(';');
            if (getComputedStyle(target).position === 'static') {
              target.dataset.aesthepdfProbePosition = target.style.position;
              target.style.position = 'relative';
            }
            target.appendChild(probe);
            return { token, text: entry.text, carry: entry.carry };
          });
        }"""
    )


def _remove_page_marker_probes(page: Any) -> None:
    page.evaluate(
        """() => {
          document.querySelectorAll('.aesthepdf-page-marker-probe').forEach((probe) => {
            const target = probe.parentElement;
            probe.remove();
            if (target && Object.hasOwn(target.dataset, 'aesthepdfProbePosition')) {
              target.style.position = target.dataset.aesthepdfProbePosition;
              delete target.dataset.aesthepdfProbePosition;
            }
          });
        }"""
    )


def _resolve_page_markers(
    page_texts: list[str],
    marker_sources: list[dict[str, Any]],
    document_title: str,
    marker_positions: list[dict[str, float]] | None = None,
    page_heights: list[float] | None = None,
) -> list[str]:
    """Resolve the section active at the top of each PDF page."""
    starts: dict[int, list[tuple[int, str, str, bool]]] = {}
    compact_pages = [re.sub(r"\s+", "", text) for text in page_texts]
    for source_index, source in enumerate(marker_sources):
        for page_index, page_text in enumerate(compact_pages):
            marker_offset = page_text.find(source["token"])
            if marker_offset != -1:
                starts.setdefault(page_index, []).append(
                    (
                        source_index,
                        source["token"],
                        source["text"],
                        source.get("carry", True),
                    )
                )
                break

    current = document_title
    resolved: list[str] = []
    for page_index, page_text in enumerate(page_texts):
        page_starts = sorted(starts.get(page_index, []))
        begins_with_section = False
        if page_starts:
            first_token = page_starts[0][1]
            if marker_positions and page_heights:
                marker_y = marker_positions[page_index].get(first_token)
                if marker_y is not None:
                    begins_with_section = marker_y >= page_heights[page_index] * 0.70
            else:
                begins_with_section = compact_pages[page_index].find(first_token) <= 120

        if page_starts and begins_with_section:
            resolved.append(page_starts[0][2])
        elif current == document_title and "目录" in page_text:
            resolved.append("目录")
        else:
            resolved.append(current)

        if page_starts:
            carrying_starts = [start for start in page_starts if start[3]]
            if carrying_starts:
                current = carrying_starts[-1][2]
    return resolved


def _read_probe_pdf(
    probe_pdf: Path, marker_sources: list[dict[str, Any]]
) -> tuple[list[str], list[dict[str, float]], list[float]]:
    """Extract marker locations from the pagination probe."""
    reader = PdfReader(str(probe_pdf))
    tokens = [source["token"] for source in marker_sources]
    page_texts: list[str] = []
    marker_positions: list[dict[str, float]] = []
    page_heights: list[float] = []

    for pdf_page in reader.pages:
        positions: dict[str, float] = {}

        def visit_text(
            text: str,
            current_transform: list[float],
            text_matrix: list[float],
            _font: dict[str, Any] | None,
            _font_size: float,
        ) -> None:
            compact_text = re.sub(r"\s+", "", text)
            for token in tokens:
                if token in compact_text:
                    positions[token] = float(
                        text_matrix[4] * current_transform[1]
                        + text_matrix[5] * current_transform[3]
                        + current_transform[5]
                    )

        page_texts.append(pdf_page.extract_text(visitor_text=visit_text) or "")
        marker_positions.append(positions)
        page_heights.append(float(pdf_page.mediabox.height))

    return page_texts, marker_positions, page_heights


def print_pdf(
    html_path: Path,
    output_pdf: Path,
    *,
    document_title: str,
    include_header_footer: bool,
    footer_title: bool = True,
    header: bool = True,
    theme: str | None = None,
) -> None:
    safe_document_title = html.escape(document_title)
    footer_inner = (
        f'<span class="pageNumber"></span> · {safe_document_title}'
        if footer_title
        else '<span class="pageNumber"></span>'
    )
    footer_template = (
        '<div style="width:100%;font-size:9px;color:#6b6a64;text-align:center;'
        'font-family:serif;padding-top:4mm;">'
        f"{footer_inner}"
        "</div>"
    )
    margin = {
        "top": "18mm" if include_header_footer else "0",
        "bottom": "24mm" if include_header_footer else "0",
        "left": "0",
        "right": "0",
    }

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(_to_file_url(html_path), wait_until="networkidle")
        page.emulate_media(media="print")

        if include_header_footer and header:
            marker_sources = _install_page_marker_probes(page)
            with tempfile.TemporaryDirectory(
                prefix="aesthepdf-pages-", dir=output_pdf.parent
            ) as page_tmp:
                page_tmp_dir = Path(page_tmp)
                probe_pdf = page_tmp_dir / "probe.pdf"
                page.pdf(
                    path=str(probe_pdf),
                    format="A4",
                    print_background=True,
                    display_header_footer=False,
                    margin=margin,
                )
                page_texts, marker_positions, page_heights = _read_probe_pdf(
                    probe_pdf, marker_sources
                )
                page_markers = _resolve_page_markers(
                    page_texts,
                    marker_sources,
                    document_title,
                    marker_positions,
                    page_heights,
                )
                _remove_page_marker_probes(page)

                parts: list[Path] = []
                for page_number, page_marker in enumerate(page_markers, start=1):
                    part = page_tmp_dir / f"page-{page_number:04d}.pdf"
                    page.pdf(
                        path=str(part),
                        format="A4",
                        print_background=True,
                        display_header_footer=True,
                        header_template=_header_template(
                            page_marker, theme=theme, enabled=True
                        ),
                        footer_template=footer_template,
                        margin=margin,
                        page_ranges=str(page_number),
                    )
                    parts.append(part)
                merge_pdfs(parts, output_pdf)
        else:
            page.pdf(
                path=str(output_pdf),
                format="A4",
                print_background=True,
                display_header_footer=include_header_footer,
                header_template="<span></span>",
                footer_template=(
                    footer_template if include_header_footer else "<span></span>"
                ),
                margin=margin,
            )
        browser.close()


def split_cover_and_body(html_path: Path, cover_html: Path, body_html: Path) -> bool:
    html = html_path.read_text(encoding="utf-8")
    if '<section class="cover-page">' not in html:
        return False

    start = html.index('<section class="cover-page">')
    cover_end = html.index("</section>", start) + len("</section>")

    head_end = html.index("</head>") + len("</head>")
    body_end = html.rindex("</body>")
    head = html[:head_end]
    tail = html[body_end:]

    cover_doc = head + html[start:cover_end] + tail
    cover_html.write_text(cover_doc, encoding="utf-8")
    body_html.write_text(head + html[cover_end:body_end] + tail, encoding="utf-8")
    return True


def merge_pdfs(parts: list[Path], output_pdf: Path) -> None:
    writer = PdfWriter()
    for part in parts:
        writer.append(str(part))
    with output_pdf.open("wb") as f:
        writer.write(f)


def render(
    input_md: Path,
    output_pdf: Path,
    *,
    theme: str = DEFAULT_THEME,
    toc: bool | None = None,
    document_title: str | None = None,
) -> Path:
    _require_tools()
    input_md = input_md.resolve()
    output_pdf = output_pdf.resolve()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    theme_config = load_theme_config(theme)
    pandoc_options = _resolve_pandoc_options(theme_config, input_md)
    defaults = theme_config.get("defaults", DEFAULT_THEME_DEFAULTS)
    use_toc = defaults.get("toc", True) if toc is None else toc
    cover = _cover_enabled(input_md, theme_config)

    with tempfile.TemporaryDirectory(prefix="aesthepdf-") as tmp:
        tmp_dir = Path(tmp)
        full_html = tmp_dir / "full.html"
        cover_html = tmp_dir / "cover.html"
        body_html = tmp_dir / "body.html"
        cover_pdf = tmp_dir / "cover.pdf"
        body_pdf = tmp_dir / "body.pdf"

        run_pandoc(
            input_md,
            full_html,
            theme_config=theme_config,
            toc=use_toc,
            theme=theme,
            cover=cover,
            pandoc_options=pandoc_options,
        )

        meta_title = document_title or read_document_title(input_md) or input_md.stem
        footer_title = defaults.get("footer_title", True)
        show_header = defaults.get("header", True)

        if cover and split_cover_and_body(full_html, cover_html, body_html):
            print_pdf(
                cover_html,
                cover_pdf,
                document_title=meta_title,
                include_header_footer=False,
                theme=theme,
            )
            print_pdf(
                body_html,
                body_pdf,
                document_title=meta_title,
                include_header_footer=True,
                footer_title=footer_title,
                header=show_header,
                theme=theme,
            )
            merge_pdfs([cover_pdf, body_pdf], output_pdf)
        else:
            print_pdf(
                full_html,
                output_pdf,
                document_title=meta_title,
                include_header_footer=True,
                footer_title=footer_title,
                header=show_header,
                theme=theme,
            )

    return output_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Render AesthePDF markdown to styled PDF")
    parser.add_argument("input", nargs="?", type=Path, help="Input markdown file")
    parser.add_argument("-o", "--output", type=Path, help="Output PDF path")
    parser.add_argument("--theme", default=None, help=f"Theme id (default: {DEFAULT_THEME})")
    parser.add_argument("--no-toc", action="store_true", help="Skip table of contents")
    parser.add_argument("--title", help="Footer document title override")
    parser.add_argument("--list-themes", action="store_true", help="List available themes")
    args = parser.parse_args()

    if args.list_themes:
        for t in list_themes():
            print(f"{t['id']:12} {t.get('name', '')} — {t.get('scenario', '')}")
        return

    if args.input is None:
        parser.error("input markdown file is required unless --list-themes is used")

    theme = args.theme or read_theme(args.input) or DEFAULT_THEME
    theme_config = load_theme_config(theme)
    default_toc = theme_config.get("defaults", {}).get("toc", True)
    use_toc = False if args.no_toc else default_toc

    output = args.output or args.input.with_suffix(".pdf")
    pdf = render(args.input, output, theme=theme, toc=use_toc, document_title=args.title)
    print(f"Wrote {pdf} (theme: {theme})")


if __name__ == "__main__":
    main()
