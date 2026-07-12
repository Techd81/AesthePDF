---
theme: manual
cover-title: AesthePDF API
subtitle: Markdown 转 PDF 渲染服务 · 完整接口与 CLI 参考手册
doc-edition: API Reference
doc-version: 2.1
doc-platform: AesthePDF Team
document-title: AesthePDF API 参考手册
lang: zh-CN
---

## 概述 {.section-header label="Ch.1"}

AesthePDF 是一套将 Markdown 渲染为精美 PDF 的文档引擎，支持五种主题
（`proposal`、`academic`、`manual`、`whitepaper`、`brief`）。本手册面向
集成开发者与运维人员，涵盖 REST API、CLI 工具、认证鉴权、错误处理与部署指南。

::: {.admonition .note}
### 版本说明

当前文档对应 **v2.1**。v2.0 起移除 `report` 主题，新增 `academic` 主题；
CLI 默认语法高亮参数改为 `--syntax-highlighting`。
:::

### 核心能力

| 能力 | 说明 |
| --- | --- |
| 同步渲染 | 上传 Markdown，直接返回 PDF 二进制 |
| 异步渲染 | 大文档提交任务，轮询或 Webhook 获取结果 |
| 主题路由 | 按 `theme` 参数加载不同 CSS / Lua filter / Pandoc 配置 |
| 封面拆分 | 封面页零边距打印，正文页带页眉页脚 |

### 服务地址

生产环境：`https://api.aesthepdf.example.com` · 本地：`http://localhost:8080`

## 快速开始 {.section-header label="Ch.2"}

::: {.admonition .tip}
### 前置条件

- Pandoc **3.x**（渲染引擎依赖）
- Python **3.10+**
- Playwright Chromium（PDF 打印）
- 有效 API Token（向管理员申请）
:::

1. 克隆仓库并安装 Python 依赖
2. 安装 Chromium 浏览器内核
3. 配置环境变量 `AESTHEPDF_TOKEN`
4. 调用 `/v1/render` 或本地 CLI 生成 PDF

```bash
git clone https://github.com/example/aesthepdf.git
cd aesthepdf
pip install -r aesthepdf/scripts/requirements.txt
python -m playwright install chromium
export AESTHEPDF_TOKEN="sk_live_xxxxxxxx"
```

最小 CLI 示例：

```bash
python aesthepdf/scripts/render.py input.md -o output.pdf --theme manual
```

最小 API 示例（curl）：

```bash
curl -X POST https://api.aesthepdf.example.com/v1/render \
  -H "Authorization: Bearer $AESTHEPDF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"markdown":"# Hello\n\nWorld","theme":"manual"}' \
  --output result.pdf
```

::: {.admonition .warning}
### 安全提示

切勿在客户端代码、前端 bundle 或公开仓库中硬编码 API Token。生产环境
应通过后端代理转发请求，Token 存储于密钥管理系统（如 Vault、KMS）。
:::

## 安装与配置 {.section-header label="Ch.3"}

### 系统依赖

```bash
# macOS
brew install pandoc

# Ubuntu / Debian
sudo apt-get install pandoc

# Windows
winget install JohnMacFarlane.Pandoc
```

验证安装：

```bash
pandoc --version   # 应 >= 3.0
python --version   # 应 >= 3.10
```

### 环境变量

| 变量 | 必填 | 说明 | 示例 |
| --- | --- | --- | --- |
| `AESTHEPDF_TOKEN` | 是 | API 认证令牌 | `sk_live_abc123` |
| `AESTHEPDF_BASE_URL` | 否 | API 基地址覆盖 | `http://localhost:8080` |
| `AESTHEPDF_TIMEOUT` | 否 | 请求超时（秒） | `120` |
| `AESTHEPDF_THEME` | 否 | 默认主题 ID | `manual` |

## 认证 {.section-header label="Ch.4"}

所有 API 请求需在 HTTP Header 中携带 Bearer Token：

```http
GET /v1/themes HTTP/1.1
Host: api.aesthepdf.example.com
Authorization: Bearer sk_live_xxxxxxxx
Accept: application/json
```

Token 分为两类：

| 类型 | 前缀 | 权限 | 适用场景 |
| --- | --- | --- | --- |
| 生产密钥 | `sk_live_` | 读写 | 服务端集成 |
| 测试密钥 | `sk_test_` | 读写（限流更严） | CI / 开发调试 |

::: {.api method="POST" path="/v1/auth/verify"}
## 验证 Token

检查当前 Token 是否有效，返回关联租户 ID 与配额信息。无需请求体。
:::

响应示例：

```json
{
  "valid": true,
  "tenant_id": "ten_abc123",
  "plan": "pro",
  "quota": {
    "renders_per_month": 10000,
    "used": 2341
  }
}
```

## 端点参考 {.section-header label="Ch.5"}

::: {.api method="GET" path="/v1/themes"}
## 列出可用主题

返回当前部署支持的所有主题 ID、显示名称与适用场景描述。
:::

::: {.api method="POST" path="/v1/render"}
## 同步渲染 PDF

接受 Markdown 正文，直接返回 `application/pdf` 二进制流。请求体最大 2 MB。
:::

请求体参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `markdown` | string | 是 | Markdown 源文本 |
| `theme` | string | 否 | 主题 ID，默认 `proposal` |
| `toc` | boolean | 否 | 是否生成目录 |
| `title` | string | 否 | 页脚标题覆盖 |
| `cover` | boolean | 否 | 是否渲染封面 |

```json
{
  "markdown": "---\ntheme: manual\ncover-title: 手册\n---\n\n## 章节\n\n正文",
  "theme": "manual",
  "toc": true,
  "title": "产品手册 v2.1"
}
```

::: {.api method="POST" path="/v1/jobs"}
## 创建异步渲染任务

适用于超过 2 MB 或预计渲染时间 > 30 s 的文档。返回 `job_id` 供轮询。
:::

::: {.api method="GET" path="/v1/jobs/{job_id}"}
## 查询任务状态

返回 `pending` / `running` / `completed` / `failed` 及进度百分比。
:::

::: {.api method="GET" path="/v1/jobs/{job_id}/download"}
## 下载任务结果

任务完成后，返回 PDF 二进制。未完成时返回 `409 Conflict`。
:::

::: {.api method="DELETE" path="/v1/jobs/{job_id}"}
## 取消渲染任务

取消排队中或运行中的任务。已完成任务不可取消。
:::

::: {.admonition .danger}
### 破坏性操作

`DELETE /v1/jobs/{job_id}` 不可恢复。若任务已接近完成，取消仍可能产生计费。
:::

## CLI 参考 {.section-header label="Ch.6"}

`render.py` 提供本地渲染能力，参数与 API 语义一致。

```bash
python aesthepdf/scripts/render.py INPUT.md [OPTIONS]
```

| 参数 | 说明 |
| --- | --- |
| `-o, --output PATH` | 输出 PDF 路径 |
| `--theme ID` | 主题（可被 frontmatter 覆盖） |
| `--no-toc` | 跳过目录 |
| `--title TEXT` | 页脚标题 |
| `--list-themes` | 列出可用主题 |

批量渲染：

```bash
for f in docs/*.md; do
  python aesthepdf/scripts/render.py "$f" \
    -o "output/$(basename "${f%.md}").pdf" --theme manual
done
```

## Markdown 扩展语法 {.section-header label="Ch.7"}

manual 主题支持以下 fenced div 组件（Pandoc 属性语法）：

### API 端点块

```markdown
::: {.api method="GET" path="/v1/example"}
## 端点标题
描述文字。
:::
```

### Admonition 提示框

| 类名 | 用途 |
| --- | --- |
| `.admonition .note` | 一般说明 |
| `.admonition .tip` | 最佳实践 |
| `.admonition .warning` | 注意事项 |
| `.admonition .danger` | 危险 / 不可逆操作 |

### 章节头

```markdown
## 章节名 {.section-header label="Ch.8"}
```

渲染为带 `Ch.N` badge 的章节标题。行内代码：`theme`、`--no-toc`。

## 错误码与排错 {.section-header label="Ch.8"}

### HTTP 状态码

| 状态码 | 含义 | 处理建议 |
| --- | --- | --- |
| 400 | 请求参数无效 | 检查 JSON 字段类型与 theme 枚举值 |
| 401 | 未授权 | 确认 Token 未过期、Header 格式正确 |
| 403 | 权限不足 | 确认 Token 类型与租户配额 |
| 404 | 资源不存在 | 检查 job_id / theme_id |
| 409 | 状态冲突 | 任务未完成即请求 download |
| 422 | Pandoc 转换失败 | 检查 Markdown 语法、fenced div 格式 |
| 429 | 请求过于频繁 | 退避重试，参考 Rate Limit 头 |
| 500 | 内部错误 | 携带 `X-Request-Id` 联系技术支持 |

错误响应体格式：

```json
{
  "error": {
    "code": "pandoc_conversion_failed",
    "message": "Lua filter error in manual.lua line 42",
    "request_id": "req_9f3a2b1c"
  }
}
```

**Q：fenced div 未渲染为 API 块？** 需使用 `::: {.api method="GET" path="/path"}` 语法。

**Q：Playwright 启动失败？** 执行 `python -m playwright install chromium`。

## 附录 {.section-header label="Ch.9"}

### 主题对照速查

| ID | 名称 | 典型用途 |
| --- | --- | --- |
| `proposal` | 方案建议书 | 客户方案、售前 |
| `academic` | 学术报告 | 论文、公式 |
| `manual` | 产品手册 | API 文档、操作手册 |
| `whitepaper` | 白皮书 | 行业研究 |
| `brief` | 执行简报 | 周报、KPI |

### 技术支持

文档：https://docs.aesthepdf.example.com · 邮件：support@aesthepdf.example.com
