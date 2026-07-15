# AesthePDF Themes

Five document types with distinct layouts, components, and Pandoc capabilities — not color swaps of the same template.

**Repository:** [github.com/Techd81/AesthePDF](https://github.com/Techd81/AesthePDF)

<p align="center">
  <img src="../../images/preview-grid.png" alt="五主题 PDF 预览拼图（3×5）" width="100%">
</p>

| ID | 名称 | 适用场景 | 结构特征 |
|----|------|----------|----------|
| `proposal` | 方案建议书 | 客户方案、建设蓝图、售前演示 | EAM 咨询风：英中 label 章节头、callout、tag |
| `academic` | 学术报告 | 论文、实验报告、技术报告 | 摘要页、数字编号章节、**MathML 公式**、图表题注 |
| `manual` | 产品手册 | 产品说明、操作手册、API 文档 | **语法高亮代码**、API 端点块、步骤圆圈、admonition |
| `whitepaper` | 白皮书 | 行业研究、技术洞察、深度长文 | 编辑排版：lead、stats、pullquote、Chapter 分隔 |
| `brief` | 执行简报 | 管理层简报、周报摘要 | KPI 卡片、时间线、待办框 |

## Usage

CLI:

```bash
python aesthepdf/scripts/render.py doc.md -o doc.pdf --theme academic
```

YAML frontmatter (overridden by `--theme` if both set):

```yaml
theme: whitepaper
cover: false   # brief 可跳过封面
```

List themes:

```bash
python aesthepdf/scripts/render.py --list-themes
```

## Choosing a theme

| User intent | Theme |
|-------------|-------|
| 给客户看的方案 / 建设蓝图 | `proposal` |
| 论文 / 实验报告 / 含公式 | `academic` |
| 行业白皮书 / 深度研究 | `whitepaper` |
| 给管理层的一页纸 / 简报 | `brief` |
| 产品文档 / API 手册 | `manual` |

## Theme configuration

Each theme in `themes/<id>/`:

```
themes/academic/
├── theme.json    # pandoc math/highlight, filters, defaults
└── style.css     # @import base.css + theme components
```

`theme.json` fields:

| Field | Purpose |
|-------|---------|
| `pandoc.from_extensions` | e.g. `tex_math_dollars` for `$...$` |
| `pandoc.math` | `mathml` (academic) or `katex` |
| `pandoc.highlight` | Pygments style e.g. `breezeDark` (manual) |
| `filters` | Lua filter chain: `section.lua` + theme filter |
| `defaults.toc` | `true` by default; use `--no-toc` to skip |
| `defaults.cover` | `false` to skip cover page |

Per-document YAML overrides (see [composition.md](../composition.md) for hybrid docs):

| Key | Effect |
|-----|--------|
| `code-highlight: true` | Manual-grade syntax highlighting on any theme |
| `syntax-highlighting: STYLE` | Pygments style (e.g. `breezeDark`) |

Shared layout: `assets/base.css`. Proposal-only components: `assets/proposal-components.css`. Code blocks: `assets/code-blocks.css`.

## Sample documents

| Theme | Template | Rendered output |
|-------|----------|-----------------|
| `proposal` | `templates/eam-sample.md` | [proposal.pdf](https://github.com/Techd81/AesthePDF/blob/main/aesthepdf_output/proposal.pdf) |
| `academic` | `templates/academic-sample.md` | [academic.pdf](https://github.com/Techd81/AesthePDF/blob/main/aesthepdf_output/academic.pdf) |
| `manual` | `templates/manual-sample.md` | [manual.pdf](https://github.com/Techd81/AesthePDF/blob/main/aesthepdf_output/manual.pdf) |
| `whitepaper` | `templates/whitepaper-sample.md` | [whitepaper.pdf](https://github.com/Techd81/AesthePDF/blob/main/aesthepdf_output/whitepaper.pdf) |
| `brief` | `templates/brief-sample.md` | [brief.pdf](https://github.com/Techd81/AesthePDF/blob/main/aesthepdf_output/brief.pdf) |

Source Markdown for all samples: [aesthepdf_output/](https://github.com/Techd81/AesthePDF/tree/main/aesthepdf_output)
