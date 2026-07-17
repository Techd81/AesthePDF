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
import unicodedata
from pathlib import Path
from typing import Any

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NumberObject
except ImportError:
    PdfReader = None
    PdfWriter = None
    NumberObject = None

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


def _footer_template(
    document_title: str,
    *,
    footer_title: bool,
    page_number: int | str | None = None,
) -> str:
    if page_number is None:
        number_html = '<span class="pageNumber"></span>'
        has_number = True
    elif page_number == "":
        number_html = ""
        has_number = False
    else:
        number_html = str(page_number)
        has_number = True

    if footer_title and has_number:
        footer_inner = f"{number_html} · {html.escape(document_title)}"
    elif footer_title:
        footer_inner = html.escape(document_title)
    else:
        footer_inner = number_html
    return (
        '<div style="width:100%;font-size:9px;color:#6b6a64;text-align:center;'
        'font-family:serif;padding-top:4mm;">'
        f"{footer_inner}"
        "</div>"
    )


def _prepare_toc_page_number_slots(page: Any) -> None:
    """Reserve TOC page-number slots before pagination so layout stays stable."""
    page.evaluate(
        """() => {
          document.querySelectorAll('#TOC > ul > li > a[href^="#"]').forEach((link) => {
            if (link.querySelector('.toc-page-num')) return;
            const title = document.createElement('span');
            title.className = 'toc-title';
            while (link.firstChild) {
              title.appendChild(link.firstChild);
            }
            const num = document.createElement('span');
            num.className = 'toc-page-num';
            num.textContent = '00';
            link.append(title, num);
          });
        }"""
    )


def _install_toc_page_probes(page: Any) -> list[dict[str, Any]]:
    """Attach probes to every top-level TOC link target for page-number resolution."""
    return page.evaluate(
        """() => {
          const decodeHref = (href) => {
            const raw = href.slice(1);
            try {
              return decodeURIComponent(raw);
            } catch {
              return raw;
            }
          };

          return [...document.querySelectorAll('#TOC > ul > li > a[href^="#"]')]
            .map((link, index) => {
              const anchorId = decodeHref(link.getAttribute('href') || '');
              if (!anchorId) return null;
              const source = document.getElementById(anchorId);
              if (!source) return null;

              let target = source;
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
              if (!target) return null;

              const token = `AESTHEPDFTOCPAGE${String(index).padStart(4, '0')}`;
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
                if (!Object.hasOwn(target.dataset, 'aesthepdfProbePosition')) {
                  target.dataset.aesthepdfProbePosition = target.style.position;
                }
                target.style.position = 'relative';
              }
              target.appendChild(probe);
              return { token, anchor_id: anchorId };
            })
            .filter(Boolean);
        }"""
    )


def _fill_toc_page_numbers(page: Any, section_pages: dict[str, int]) -> None:
    """Write resolved body page numbers into prepared TOC slots."""
    page.evaluate(
        """(sectionPages) => {
          document.querySelectorAll('#TOC > ul > li > a[href^="#"]').forEach((link) => {
            const raw = link.getAttribute('href').slice(1);
            let id;
            try {
              id = decodeURIComponent(raw);
            } catch {
              id = raw;
            }
            const pageNumber = sectionPages[id];
            const num = link.querySelector('.toc-page-num');
            if (pageNumber == null || !num) return;
            num.textContent = String(pageNumber).padStart(2, '0');
          });
        }""",
        section_pages,
    )


def _section_start_pages(
    page_texts: list[str],
    marker_sources: list[dict[str, Any]],
) -> dict[str, int]:
    """Map heading anchor ids to 1-based body page numbers."""
    compact_pages = [re.sub(r"\s+", "", text) for text in page_texts]
    pages: dict[str, int] = {}
    for source in marker_sources:
        anchor_id = source.get("anchor_id")
        if not anchor_id:
            continue
        token = source["token"]
        for page_index, page_text in enumerate(compact_pages):
            if token in page_text:
                pages[anchor_id] = page_index + 1
                break
    return pages


def _content_page_offset(
    page_markers: list[str],
    marker_sources: list[dict[str, Any]],
) -> int:
    """0-based index of the first chapter page (after TOC / abstract front matter)."""
    front_matter_titles = {
        source["text"]
        for source in marker_sources
        if not source.get("carry", True) or not source.get("anchor_id")
    }
    chapter_titles = {
        source["text"]
        for source in marker_sources
        if source.get("carry", True) and source.get("anchor_id")
    }
    for page_index, marker in enumerate(page_markers):
        if marker in chapter_titles and marker not in front_matter_titles:
            return page_index
    for page_index, marker in enumerate(page_markers):
        if marker not in front_matter_titles:
            return page_index
    return 0


def _toc_display_pages(
    page_markers: list[str],
    page_texts: list[str],
    toc_probes: list[dict[str, Any]],
    marker_sources: list[dict[str, Any]],
    content_offset: int,
) -> dict[str, int]:
    """Map TOC anchor ids to content-relative page numbers."""
    title_by_anchor = {
        source["anchor_id"]: source["text"]
        for source in marker_sources
        if source.get("anchor_id")
    }
    pages: dict[str, int] = {}
    for probe in toc_probes:
        anchor_id = probe.get("anchor_id")
        if not anchor_id:
            continue
        title = title_by_anchor.get(anchor_id)
        if title:
            for page_index, marker in enumerate(page_markers):
                if page_index < content_offset:
                    continue
                if marker == title:
                    pages[anchor_id] = page_index - content_offset + 1
                    break
        if anchor_id in pages:
            continue
        physical = _section_start_pages(page_texts, [probe]).get(anchor_id)
        if physical is not None and physical > content_offset:
            pages[anchor_id] = physical - content_offset
    return pages


def _displayed_page_numbers(
    physical_pages: dict[str, int],
    content_offset: int,
) -> dict[str, int]:
    """Convert 1-based physical body pages to content-relative numbers."""
    return {
        anchor_id: physical - content_offset
        for anchor_id, physical in physical_pages.items()
        if physical > content_offset
    }


def _install_page_marker_probes(page: Any) -> list[dict[str, Any]]:
    """Attach extractable, visually transparent tokens to running-header sources."""
    return page.evaluate(
        """() => {
          const entries = [...document.querySelectorAll('.document-body h2.section-header')]
            .map((source) => {
              const probeText = [...source.childNodes]
                .filter((node) => {
                  return !(
                    node.nodeType === Node.ELEMENT_NODE
                    && node.classList?.contains('aesthepdf-page-marker-probe')
                  );
                })
                .map((node) => node.textContent || '')
                .join('')
                .trim();
              return {
                source,
                text: source.getAttribute('page-header')
                  || source.getAttribute('data-page-header')
                  || probeText
                  || source.textContent.trim(),
                carry: true,
              };
            });

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
            return {
              token,
              text: entry.text,
              carry: entry.carry,
              anchor_id: entry.source.id || '',
            };
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
            toc_present = page.query_selector("#TOC") is not None
            marker_sources = _install_page_marker_probes(page)
            toc_probes: list[dict[str, Any]] = []
            if toc_present:
                # Install after header markers so section titles stay clean.
                _prepare_toc_page_number_slots(page)
                toc_probes = _install_toc_page_probes(page)
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
                    probe_pdf, marker_sources + toc_probes
                )
                page_markers = _resolve_page_markers(
                    page_texts,
                    marker_sources,
                    document_title,
                    marker_positions,
                    page_heights,
                )
                content_offset = _content_page_offset(page_markers, marker_sources)
                if toc_present:
                    _fill_toc_page_numbers(
                        page,
                        _toc_display_pages(
                            page_markers,
                            page_texts,
                            toc_probes,
                            marker_sources,
                            content_offset,
                        ),
                    )
                _remove_page_marker_probes(page)

                base_pdf = page_tmp_dir / "base.pdf"
                page.pdf(
                    path=str(base_pdf),
                    format="A4",
                    print_background=True,
                    display_header_footer=False,
                    margin=margin,
                )

                base_page_count = len(PdfReader(str(base_pdf)).pages)
                if base_page_count != len(page_markers):
                    raise RuntimeError(
                        "Pagination changed after resolving running headers: "
                        f"probe={len(page_markers)}, body={base_page_count}"
                    )

                overlay_page = browser.new_page()
                overlay_page.set_content(
                    "<!doctype html><html><head><style>"
                    "@page{size:A4;margin:0}html,body{margin:0;background:transparent}"
                    "</style></head><body></body></html>",
                    wait_until="load",
                )
                overlays: list[Path] = []
                for page_index, page_marker in enumerate(page_markers):
                    overlay = page_tmp_dir / f"overlay-{page_index + 1:04d}.pdf"
                    if page_index < content_offset:
                        display_page: int | str = ""
                    else:
                        display_page = page_index - content_offset + 1
                    overlay_page.pdf(
                        path=str(overlay),
                        format="A4",
                        print_background=False,
                        display_header_footer=True,
                        header_template=_header_template(
                            page_marker, theme=theme, enabled=True
                        ),
                        footer_template=_footer_template(
                            document_title,
                            footer_title=footer_title,
                            page_number=display_page,
                        ),
                        margin=margin,
                    )
                    overlays.append(overlay)
                overlay_page.close()
                merge_pdf_overlays(base_pdf, overlays, output_pdf)
        else:
            with tempfile.TemporaryDirectory(
                prefix="aesthepdf-print-", dir=output_pdf.parent
            ) as print_tmp:
                raw_pdf = Path(print_tmp) / "raw.pdf"
                page.pdf(
                    path=str(raw_pdf),
                    format="A4",
                    print_background=True,
                    display_header_footer=include_header_footer,
                    header_template="<span></span>",
                    footer_template=(
                        _footer_template(document_title, footer_title=footer_title)
                        if include_header_footer
                        else "<span></span>"
                    ),
                    margin=margin,
                )
                normalize_pdf(raw_pdf, output_pdf)
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


_BFCHAR_BLOCK_RE = re.compile(
    rb"(?P<count>\d+)\s+beginbfchar(?P<body>.*?)endbfchar",
    re.DOTALL,
)
_BFCHAR_ENTRY_RE = re.compile(
    rb"(?P<prefix><[0-9A-Fa-f]+>\s+)<(?P<target>[0-9A-Fa-f]+)>"
)
_BFRANGE_BLOCK_RE = re.compile(
    rb"(?P<count>\d+)\s+beginbfrange(?P<body>.*?)endbfrange",
    re.DOTALL,
)
_BFRANGE_LINE_RE = re.compile(
    rb"^(?P<prefix>\s*<(?P<start>[0-9A-Fa-f]+)>\s+"
    rb"<(?P<end>[0-9A-Fa-f]+)>\s+)(?P<targets>.*)$"
)
_HEX_TOKEN_RE = re.compile(rb"<(?P<target>[0-9A-Fa-f]+)>")
# Canonical CJK radical mappings plus Chromium's private-use aliases for
# punctuation and ordered-list markers in the bundled CFF fonts.
_PDF_TEXT_TRANSLATION = str.maketrans(
    {
        "\u2ea6": "\u4e2c",
        "\u2eb0": "\u7e9f",
        "\u2ec5": "\u89c1",
        "\u2ec6": "\u89d2",
        "\u2ec8": "\u8ba0",
        "\u2ec9": "\u8d1d",
        "\u2ecb": "\u8f66",
        "\u2ed0": "\u9485",
        "\u2ed3": "\u957f",
        "\u2ed4": "\u95e8",
        "\u2ed9": "\u97e6",
        "\u2eda": "\u9875",
        "\u2edb": "\u98ce",
        "\u2edc": "\u98de",
        "\u2ee0": "\u9963",
        "\u2ee2": "\u9a6c",
        "\u2ee5": "\u9c7c",
        "\u2ee6": "\u9e1f",
        "\u2ee7": "\u5364",
        "\u2ee8": "\u9ea6",
        "\u2ee9": "\u9ec4",
        "\u2eea": "\u9efe",
        "\u2eeb": "\u6589",
        "\u2eec": "\u9f50",
        "\u2eed": "\u6b6f",
        "\u2eee": "\u9f7f",
        "\u2eef": "\u7adc",
        "\u2ef0": "\u9f99",
        "\u2ef2": "\u4e80",
        "\u2ef3": "\u9f9f",
        "\ue072": "1",
        "\ue073": "2",
        "\ue074": "3",
        "\ue075": "4",
        "\ue076": "5",
        "\ue077": "6",
        "\ue078": "7",
        "\ue079": "8",
        "\ue07a": "9",
        "\ue088": "-",
        "\ue089": "-",
        "\ue092": ":",
        "\ue094": ".",
        "\ue09d": "+",
        "\ue09f": "×",
    }
)


def _normalize_unicode_hex(target: bytes) -> bytes:
    if len(target) % 4 != 0:
        return target
    try:
        text = bytes.fromhex(target.decode("ascii")).decode("utf-16-be")
    except (UnicodeDecodeError, ValueError):
        return target

    normalized = unicodedata.normalize(
        "NFKC", text.translate(_PDF_TEXT_TRANSLATION)
    ).replace("\x01", " ")
    if normalized == text:
        return target
    return normalized.encode("utf-16-be").hex().upper().encode("ascii")


def _normalize_cmap_data(data: bytes) -> bytes:
    """Normalize compatibility characters in PDF ToUnicode CMaps."""

    def replace_bfchar_block(match: re.Match[bytes]) -> bytes:
        body = _BFCHAR_ENTRY_RE.sub(
            lambda entry: entry.group("prefix")
            + b"<"
            + _normalize_unicode_hex(entry.group("target"))
            + b">",
            match.group("body"),
        )
        return (
            match.group("count")
            + b" beginbfchar"
            + body
            + b"endbfchar"
        )

    def replace_bfrange_block(match: re.Match[bytes]) -> bytes:
        lines: list[bytes] = []
        for line in match.group("body").splitlines(keepends=True):
            parsed = _BFRANGE_LINE_RE.match(line.rstrip(b"\r\n"))
            if parsed is None:
                lines.append(line)
                continue

            targets = parsed.group("targets")
            is_array = targets.lstrip().startswith(b"[")
            if is_array:
                targets = _HEX_TOKEN_RE.sub(
                    lambda token: b"<"
                    + _normalize_unicode_hex(token.group("target"))
                    + b">",
                    targets,
                )
            else:
                scalar = _HEX_TOKEN_RE.fullmatch(targets.strip())
                if scalar is not None and len(scalar.group("target")) == 4:
                    start = int(parsed.group("start"), 16)
                    end = int(parsed.group("end"), 16)
                    destination = int(scalar.group("target"), 16)
                    if 0 <= end - start <= 512:
                        original_targets = [
                            f"{destination + offset:04X}".encode("ascii")
                            for offset in range(end - start + 1)
                        ]
                        normalized_targets = [
                            _normalize_unicode_hex(target)
                            for target in original_targets
                        ]
                        if normalized_targets != original_targets:
                            targets = (
                                b"["
                                + b" ".join(
                                    b"<" + target + b">"
                                    for target in normalized_targets
                                )
                                + b"]"
                            )
            newline = b"\r\n" if line.endswith(b"\r\n") else b"\n" if line.endswith(b"\n") else b""
            lines.append(parsed.group("prefix") + targets + newline)

        return (
            match.group("count")
            + b" beginbfrange"
            + b"".join(lines)
            + b"endbfrange"
        )

    normalized = _BFCHAR_BLOCK_RE.sub(replace_bfchar_block, data)
    return _BFRANGE_BLOCK_RE.sub(replace_bfrange_block, normalized)


def _normalize_pdf_unicode_mappings(writer: Any) -> None:
    seen: set[tuple[int, int] | int] = set()
    for page in writer.pages:
        resources = page.get("/Resources")
        if resources is None:
            continue
        resources = resources.get_object()
        fonts = resources.get("/Font")
        if fonts is None:
            continue
        fonts = fonts.get_object()
        for font_ref in fonts.values():
            font = font_ref.get_object()
            to_unicode_ref = font.get("/ToUnicode")
            if to_unicode_ref is None:
                continue
            stream = to_unicode_ref.get_object()
            reference = getattr(stream, "indirect_reference", None)
            key: tuple[int, int] | int = (
                (reference.idnum, reference.generation)
                if reference is not None
                else id(stream)
            )
            if key in seen:
                continue
            seen.add(key)
            data = stream.get_data()
            normalized = _normalize_cmap_data(data)
            if normalized != data:
                stream.set_data(normalized)


def _write_pdf(writer: Any, output_pdf: Path) -> None:
    _normalize_pdf_unicode_mappings(writer)
    with output_pdf.open("wb") as file:
        writer.write(file)


def normalize_pdf(input_pdf: Path, output_pdf: Path) -> None:
    reader = PdfReader(str(input_pdf))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    _write_pdf(writer, output_pdf)


def merge_pdf_overlays(
    base_pdf: Path, overlays: list[Path], output_pdf: Path
) -> None:
    reader = PdfReader(str(base_pdf))
    if len(reader.pages) != len(overlays):
        raise RuntimeError(
            f"Overlay count mismatch: pages={len(reader.pages)}, overlays={len(overlays)}"
        )

    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    for page, overlay_path in zip(writer.pages, overlays, strict=True):
        overlay_reader = PdfReader(str(overlay_path))
        if len(overlay_reader.pages) != 1:
            raise RuntimeError(f"Expected one-page overlay: {overlay_path}")
        overlay_page = overlay_reader.pages[0]
        if "/Annots" in overlay_page:
            del overlay_page["/Annots"]
        page.merge_page(overlay_page, over=True)
    _write_pdf(writer, output_pdf)


def merge_pdfs(parts: list[Path], output_pdf: Path) -> None:
    if not parts:
        raise ValueError("At least one PDF is required")

    body_reader = PdfReader(str(parts[-1]))
    writer = PdfWriter()
    writer.clone_document_from_reader(body_reader)
    prefix_page_count = 0
    for part in reversed(parts[:-1]):
        prefix_reader = PdfReader(str(part))
        prefix_page_count += len(prefix_reader.pages)
        for page in reversed(prefix_reader.pages):
            writer.insert_page(page, index=0)
    if prefix_page_count:
        _shift_numeric_link_destinations(writer, prefix_page_count)
    _write_pdf(writer, output_pdf)


def _shift_numeric_link_destinations(writer: Any, offset: int) -> None:
    """Shift page-index link destinations after prefix pages are inserted."""
    for page in writer.pages[offset:]:
        for annotation_ref in page.get("/Annots") or []:
            annotation = annotation_ref.get_object()
            if annotation.get("/Subtype") != "/Link":
                continue
            destination = annotation.get("/Dest")
            if destination is None:
                action = annotation.get("/A")
                if action is not None:
                    action = action.get_object()
                    if action.get("/S") == "/GoTo":
                        destination = action.get("/D")
            if (
                destination is not None
                and len(destination) > 0
                and isinstance(destination[0], NumberObject)
            ):
                destination[0] = NumberObject(int(destination[0]) + offset)


def _validate_io_paths(input_md: Path, output_pdf: Path) -> tuple[Path, Path]:
    input_md = input_md.resolve()
    output_pdf = output_pdf.resolve()
    if not input_md.is_file():
        raise SystemExit(f"Input Markdown not found: {input_md}")
    if output_pdf.suffix.lower() != ".pdf":
        raise SystemExit(f"Output path must end in .pdf: {output_pdf}")
    if input_md == output_pdf:
        raise SystemExit("Input Markdown and output PDF must use different paths")
    return input_md, output_pdf


def render(
    input_md: Path,
    output_pdf: Path,
    *,
    theme: str = DEFAULT_THEME,
    toc: bool | None = None,
    document_title: str | None = None,
) -> Path:
    _require_tools()
    input_md, output_pdf = _validate_io_paths(input_md, output_pdf)
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

    if not args.input.is_file():
        parser.error(f"input markdown file not found: {args.input}")

    output = args.output or args.input.with_suffix(".pdf")
    try:
        _validate_io_paths(args.input, output)
    except SystemExit as exc:
        parser.error(str(exc))

    theme = args.theme or read_theme(args.input) or DEFAULT_THEME
    theme_config = load_theme_config(theme)
    default_toc = theme_config.get("defaults", {}).get("toc", True)
    use_toc = False if args.no_toc else default_toc

    pdf = render(args.input, output, theme=theme, toc=use_toc, document_title=args.title)
    print(f"Wrote {pdf} (theme: {theme})")


if __name__ == "__main__":
    main()
