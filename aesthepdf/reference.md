# AesthePDF Design Reference

Visual baseline for the default **proposal** theme: `doc/EAM智能场景建设方案(1).pdf`.

Other themes share the same Markdown components but override tokens in `themes/<id>/style.css`. See [themes/README.md](themes/README.md).

## Design tokens

Extracted from reference PDF. Defined in `assets/style.css` as CSS custom properties.

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-page` | `#f5f4ed` | Page background (cream) |
| `--bg-panel` | `#faf9f5` | Callout box fill |
| `--bg-tag` | `#e4ecf5` | Inline tag pill fill |
| `--text-primary` | `#141413` | Titles |
| `--text-body` | `#3d3d3a` | Body copy |
| `--text-muted` | `#6b6a64` | Footer, TOC numbers |
| `--text-label` | `#1b365d` | English section labels, tags |
| `--accent` | `#1b365d` | Vertical bars, bullets, borders |

## Typography

| Element | Size | Weight | Notes |
|---------|------|--------|-------|
| Cover English label | 10pt | 400 | Uppercase, letter-spacing 0.12em |
| Cover title | 34pt | 700 | Chinese main title |
| Cover subtitle | 14pt | 400 | Line-height 1.65 |
| Section English label | 10pt | 400 | e.g. `01 · EXECUTIVE SUMMARY` |
| Section Chinese title | 22pt | 700 | Left navy bar 3px |
| Body | 12pt | 400 | Line-height 1.75, justified |
| H3 / callout title | 13pt | 700 | |
| Table | 10.5pt | 400 | Header row bold |
| Footer | 9pt | 400 | `{page} · {document-title}` |

Font stack: **TsangerShuYuan** (`fonts/TsangerShuYuanT-W02/W03/W04.ttf`).

Reference PDF used TsangerJinKai02; ShuYuan is the bundled substitute.

## Page layout

| Property | Value |
|----------|-------|
| Size | A4 (210 × 297 mm) |
| Content margins | ~20mm left/right (CSS padding), 18mm top / 24mm bottom (`@page` + Playwright) |
| Cover | Full-bleed cream, no header/footer |
| Accent bar width | 3px solid `--accent` |

## Components

### Cover (`assets/template.html`)

Rendered from YAML: `cover-title`, `title-en`, `subtitle`, `doc-platform`, `doc-version`, `doc-date`, `doc-edition`.

### Table of contents

Pandoc `--toc` inside `.toc-page`. Styled via `#TOC` rules in CSS.

TOC page numbers use CSS `target-counter()`; if missing in output, content structure is still correct — re-render after content changes.

### Section header

Markdown:

```markdown
## 执行摘要 {.section-header label="01 · EXECUTIVE SUMMARY"}
```

HTML structure:

```html
<h2 class="section-header" data-label="01 · EXECUTIVE SUMMARY" id="执行摘要">执行摘要</h2>
```

### Tag pill

Markdown: `[智能问答]{.tag}`

### Callout

Markdown:

```markdown
::: callout
### Title

Body paragraph.
:::
```

First heading inside becomes `.callout-title`. Left navy border + rounded right corners.

### Table

Pipe table, no vertical borders. Header bottom rule + subtle row separators.

## Print pipeline notes

1. **Pandoc** converts structure; **CSS** controls aesthetics.
2. **Cover** prints without header/footer; **body** prints with Playwright header/footer templates.
3. **`print_background: true`** is required or cream background and tags disappear.
4. Font paths in CSS are relative to the HTML file location; keep `fonts/` at repo root.

## Visual checklist

- [ ] Cream background on every page
- [ ] Cover: English label → large title → subtitle → footer meta block
- [ ] TOC: "目录" with left accent bar
- [ ] Sections: English label above Chinese title with left bar
- [ ] Tags: light blue pills inline
- [ ] Callouts: tinted panel, navy left edge
- [ ] Tables: minimal horizontal rules only
- [ ] Footer: `{n} · {document-title}` centered
