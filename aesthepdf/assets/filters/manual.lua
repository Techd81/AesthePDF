-- Manual: API endpoint blocks, admonitions

local function read_attr(el, key)
  return el.attributes[key] or el.attributes["data-" .. key]
end

function Div(el)
  if el.classes:includes("api") then
    local method = read_attr(el, "method") or "GET"
    local path = read_attr(el, "path") or ""
    local body = pandoc.List(el.content)
    if #body > 0 and body[1].t == "Header" then
      body:remove(1)
    end
    local html = string.format(
      [[<div class="api-block">
  <div class="api-endpoint"><span class="api-method api-method-%s">%s</span><span class="api-path">%s</span></div>
  <div class="api-body">%s</div>
</div>]],
      method:lower(),
      method:upper(),
      path,
      pandoc.write(pandoc.Pandoc(body), "html")
    )
    return pandoc.RawBlock("html", html)
  end

  if el.classes:includes("admonition") then
    local kind = "note"
    for _, cls in ipairs(el.classes) do
      if cls ~= "admonition" then
        kind = cls
      end
    end
    local title_map = { note = "说明", warning = "警告", tip = "提示", danger = "危险" }
    local title = title_map[kind] or kind
    local body = pandoc.List(el.content)
    if #body > 0 and body[1].t == "Header" then
      title = pandoc.utils.stringify(body[1])
      body:remove(1)
    end
    local html = string.format(
      [[<div class="admonition admonition-%s">
  <div class="admonition-title">%s</div>
  <div class="admonition-body">%s</div>
</div>]],
      kind,
      title,
      pandoc.write(pandoc.Pandoc(body), "html")
    )
    return pandoc.RawBlock("html", html)
  end

  return nil
end

function Header(el)
  if el.classes:includes("section-header") then
    local label = read_attr(el, "label") or ""
    local title = pandoc.utils.stringify(el)
    local html = string.format(
      [[<div class="manual-section">
  <span class="manual-chapter">%s</span>
  <h2 class="manual-title">%s</h2>
</div>]],
      label,
      title
    )
    -- Keep original Header for TOC; hide visually via CSS
    el.classes:insert("manual-toc-source")
    return { el, pandoc.RawBlock("html", html) }
  end
  return nil
end
