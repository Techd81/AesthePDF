from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Link


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "aesthepdf" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import render  # noqa: E402


class ComponentFilterTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("pandoc"), "pandoc is required")
    def test_documented_multiline_components_render_every_record(self) -> None:
        cases = [
            (
                "brief",
                REPO_ROOT / "aesthepdf" / "templates" / "brief-sample.md",
                {"kpi-card": 12, "timeline-item": 17},
            ),
            (
                "whitepaper",
                REPO_ROOT
                / "aesthepdf"
                / "templates"
                / "whitepaper-sample.md",
                {"stat-item": 6},
            ),
        ]

        for theme, markdown, expected in cases:
            with self.subTest(theme=theme), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "output.html"
                config = render.load_theme_config(theme)
                render.run_pandoc(
                    markdown,
                    output,
                    theme_config=config,
                    toc=True,
                    theme=theme,
                    cover=True,
                    pandoc_options=render._resolve_pandoc_options(config, markdown),
                )
                html = output.read_text(encoding="utf-8")
                for class_name, count in expected.items():
                    self.assertEqual(html.count(f'class="{class_name}'), count)

    @unittest.skipUnless(shutil.which("pandoc"), "pandoc is required")
    def test_component_record_text_is_html_escaped(self) -> None:
        source = """---
theme: whitepaper
---

::: stats
1<2|A & B
:::
"""
        with tempfile.TemporaryDirectory() as tmp:
            markdown = Path(tmp) / "input.md"
            output = Path(tmp) / "output.html"
            markdown.write_text(source, encoding="utf-8")
            config = render.load_theme_config("whitepaper")
            render.run_pandoc(
                markdown,
                output,
                theme_config=config,
                toc=False,
                theme="whitepaper",
                cover=False,
            )
            html = output.read_text(encoding="utf-8")
            self.assertIn("1&lt;2", html)
            self.assertIn("A &amp; B", html)


class PdfPostProcessingTests(unittest.TestCase):
    def test_section_start_pages_maps_anchor_ids(self) -> None:
        marker_sources = [
            {
                "token": "AESTHEPDFMARKER0000",
                "text": "目录",
                "carry": False,
                "anchor_id": "",
            },
            {
                "token": "AESTHEPDFMARKER0001",
                "text": "执行摘要",
                "carry": True,
                "anchor_id": "执行摘要",
            },
            {
                "token": "AESTHEPDFMARKER0002",
                "text": "建设蓝图",
                "carry": True,
                "anchor_id": "建设蓝图",
            },
        ]
        page_texts = [
            "目录 AESTHEPDFMARKER0000",
            "正文开头",
            "执行摘要 AESTHEPDFMARKER0001 内容",
            "建设蓝图 AESTHEPDFMARKER0002 内容",
        ]
        self.assertEqual(
            render._section_start_pages(page_texts, marker_sources),
            {"执行摘要": 3, "建设蓝图": 4},
        )

    def test_content_page_offset_skips_toc_front_matter(self) -> None:
        marker_sources = [
            {
                "token": "AESTHEPDFMARKER0000",
                "text": "目录",
                "carry": False,
                "anchor_id": "",
            },
            {
                "token": "AESTHEPDFMARKER0001",
                "text": "执行摘要",
                "carry": True,
                "anchor_id": "执行摘要",
            },
        ]
        page_markers = ["目录", "执行摘要", "执行摘要"]
        offset = render._content_page_offset(page_markers, marker_sources)
        self.assertEqual(offset, 1)
        self.assertEqual(
            render._displayed_page_numbers({"执行摘要": 2, "蓝图": 4}, offset),
            {"执行摘要": 1, "蓝图": 3},
        )

    def test_content_page_offset_skips_abstract_before_chapter(self) -> None:
        marker_sources = [
            {
                "token": "AESTHEPDFMARKER0000",
                "text": "目录",
                "carry": False,
                "anchor_id": "",
            },
            {
                "token": "AESTHEPDFMARKER0001",
                "text": "摘要",
                "carry": True,
                "anchor_id": "",
            },
            {
                "token": "AESTHEPDFMARKER0002",
                "text": "引言",
                "carry": True,
                "anchor_id": "引言",
            },
            {
                "token": "AESTHEPDFMARKER0003",
                "text": "相关工作",
                "carry": True,
                "anchor_id": "相关工作",
            },
        ]
        page_markers = ["目录", "摘要", "引言", "相关工作"]
        self.assertEqual(
            render._content_page_offset(page_markers, marker_sources),
            2,
        )
        self.assertEqual(
            render._toc_display_pages(
                page_markers,
                ["目录", "摘要", "引言", "相关工作"],
                [
                    {"token": "T0", "anchor_id": "引言"},
                    {"token": "T1", "anchor_id": "相关工作"},
                ],
                marker_sources,
                2,
            ),
            {"引言": 1, "相关工作": 2},
        )

    def test_cmap_normalization_repairs_radicals_and_control_separators(self) -> None:
        cmap = b"""5 beginbfchar
<01> <2F2F>
<02> <2EDA>
<03> <0001>
<04> <E088>
<05> <E09D>
endbfchar
"""
        normalized = render._normalize_cmap_data(cmap)
        self.assertIn(b"<01> <5DE5>", normalized)
        self.assertIn(b"<02> <9875>", normalized)
        self.assertIn(b"<03> <0020>", normalized)
        self.assertIn(b"<04> <002D>", normalized)
        self.assertIn(b"<05> <002B>", normalized)

    def test_cmap_normalization_expands_affected_unicode_ranges(self) -> None:
        cmap = b"""2 beginbfrange
<55> <58> <E072>
<C4> <C5> <E088>
endbfrange
"""
        normalized = render._normalize_cmap_data(cmap)
        self.assertIn(b"<55> <58> [<0031> <0032> <0033> <0034>]", normalized)
        self.assertIn(b"<C4> <C5> [<002D> <002D>]", normalized)

    def test_overlay_merge_preserves_internal_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base.pdf"
            overlay = root / "overlay.pdf"
            output = root / "output.pdf"

            base_writer = PdfWriter()
            base_writer.add_blank_page(width=595, height=842)
            base_writer.add_blank_page(width=595, height=842)
            base_writer.add_annotation(
                page_number=0,
                annotation=Link(rect=(10, 10, 100, 30), target_page_index=1),
            )
            base_writer.add_named_destination("target", 1)
            with base.open("wb") as file:
                base_writer.write(file)

            overlay_writer = PdfWriter()
            overlay_writer.add_blank_page(width=595, height=842)
            with overlay.open("wb") as file:
                overlay_writer.write(file)

            render.merge_pdf_overlays(base, [overlay, overlay], output)
            reader = PdfReader(output)
            self.assertEqual(len(reader.pages), 2)
            self.assertEqual(len(reader.pages[0].get("/Annots") or []), 1)
            self.assertIn("target", reader.named_destinations)

    def test_cover_prepend_preserves_internal_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cover = root / "cover.pdf"
            body = root / "body.pdf"
            output = root / "output.pdf"

            cover_writer = PdfWriter()
            cover_writer.add_blank_page(width=595, height=842)
            with cover.open("wb") as file:
                cover_writer.write(file)

            body_writer = PdfWriter()
            body_writer.add_blank_page(width=595, height=842)
            body_writer.add_blank_page(width=595, height=842)
            body_writer.add_annotation(
                page_number=0,
                annotation=Link(rect=(10, 10, 100, 30), target_page_index=1),
            )
            with body.open("wb") as file:
                body_writer.write(file)

            render.merge_pdfs([cover, body], output)
            reader = PdfReader(output)
            self.assertEqual(len(reader.pages), 3)
            self.assertEqual(len(reader.pages[1].get("/Annots") or []), 1)
            annotation = reader.pages[1]["/Annots"][0].get_object()
            self.assertEqual(int(annotation["/Dest"][0]), 2)


class InputValidationTests(unittest.TestCase):
    def test_missing_input_is_rejected_without_opening_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(SystemExit, "Input Markdown not found"):
                render._validate_io_paths(root / "missing.md", root / "out.pdf")

    def test_non_pdf_output_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.md"
            source.write_text("# Test", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "must end in .pdf"):
                render._validate_io_paths(source, Path(tmp) / "output.md")

    def test_input_cannot_be_overwritten_by_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "same.pdf"
            source.write_text("# Markdown despite the suffix", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "different paths"):
                render._validate_io_paths(source, source)


if __name__ == "__main__":
    unittest.main()
