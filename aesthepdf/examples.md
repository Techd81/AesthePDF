# AesthePDF Examples

## Minimal proposal

```markdown
---
theme: proposal
cover-title: 项目方案
title-en: PROJECT PROPOSAL
subtitle: 一句话描述本方案范围与价值。
doc-platform: 某某平台
doc-version: V1.0
doc-date: 2026.07
doc-edition: 内部讨论版
document-title: 项目方案
lang: zh-CN
---

## 概述 {.section-header label="01 · OVERVIEW"}

正文段落。
```

## Academic — formulas and abstract

```markdown
---
theme: academic
cover-title: 研究标题
doc-authors: 作者甲 · 作者乙
doc-institution: 某某大学
---

::: abstract
## 摘要
本文研究了……
:::

## 引言 {.section-header label="1"}

行内公式 $E=mc^2$，独立公式：

$$
\int_0^1 x\, dx = \frac{1}{2}
$$

::: {.figure caption="Figure 1. 示意图"}
图注内容。
:::
```

## Academic + code (hybrid)

Tutorial or theory+code docs: keep **`theme: academic`**, enable **`code-highlight: true`**.

```markdown
---
theme: academic
code-highlight: true
cover-title: Transformer 原理学习与代码入手指南
document-title: Transformer 学习与实战
lang: zh-CN
---

::: abstract
## 摘要
本文介绍 Transformer 核心原理与最小 PyTorch 实现。
:::

## 注意力机制 {.section-header label="1"}

```python
import torch
attn = torch.softmax(scores, dim=-1)
```
```

## Whitepaper + code (hybrid)

Primary `whitepaper` for editorial layout; layer code highlighting.

```markdown
---
theme: whitepaper
code-highlight: true
cover-title: 大模型推理优化白皮书
---
```

## Manual — code and API blocks

```markdown
---
theme: manual
cover-title: API 文档
doc-edition: API Reference
doc-version: 1.0
---

## 认证 {.section-header label="Ch.1"}

```python
import requests
resp = requests.get("/v1/themes")
```

::: {.api method="GET" path="/v1/users/{id}"}
## 获取用户
返回指定 ID 的用户信息。
:::

::: {.admonition .warning}
### 注意
Token 不可泄露。
:::
```

## Whitepaper — editorial components

```markdown
---
theme: whitepaper
cover-title: 行业白皮书
title-en: INDUSTRY RESEARCH
doc-edition: Research Report · 深度研究
---

::: stats
42%|已部署预测性维护
3.2x|ROI 中位数
:::

## 背景 {.section-header label="Chapter 01"}

::: lead
章节导语，放大灰色首段。
:::

::: pullquote
「关键引文。」
:::

::: insight
### 核心洞察
编辑风格的洞察框。
:::
```

## Brief — KPIs and timeline

```markdown
---
theme: brief
cover-title: 周报
doc-date: 2026-W24
doc-platform: 运维部
---

::: kpis
可用率|98%|↑ 0.3%
闭环率|76%|↓ 4%
:::

## 本周概览 {.section-header}

::: timeline
06-09|场景上线灰度
06-11|UAT 通过
:::

::: action
### 待决策
1. 预算追加确认
:::

[完成]{.status-done} [风险]{.status-risk}
```

## Render all samples

```bash
python aesthepdf/scripts/render.py aesthepdf/templates/eam-sample.md -o output/proposal.pdf
python aesthepdf/scripts/render.py aesthepdf/templates/academic-sample.md -o output/academic.pdf --theme academic
python aesthepdf/scripts/render.py aesthepdf/templates/manual-sample.md -o output/manual.pdf --theme manual
python aesthepdf/scripts/render.py aesthepdf/templates/whitepaper-sample.md -o output/whitepaper.pdf --theme whitepaper
python aesthepdf/scripts/render.py aesthepdf/templates/brief-sample.md -o output/brief.pdf --theme brief
```

## Agent drafting pattern

1. Pick **primary** theme by document genre ([composition.md](composition.md)).
2. Scan outline for secondary capabilities; layer frontmatter (`code-highlight`, etc.).
3. Create **`aesthepdf_output/`** at workspace root if missing.
4. Write **`aesthepdf_output/{slug}.md`**.
5. Render: `python <skill-dir>/scripts/render.py aesthepdf_output/{slug}.md -o aesthepdf_output/{slug}.pdf --theme <primary>`
6. Deliver **`aesthepdf_output/{slug}.pdf`**.

Do not write `.md`/`.pdf` to workspace root. Do not hand-write PDF bytes.
