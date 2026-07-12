-- Academic: abstract, figure, equation

local function read_attr(el, key)
  return el.attributes[key] or el.attributes["data-" .. key]
end

function Div(el)
  if el.classes:includes("abstract") then
    local title = "摘要"
    local body = pandoc.List()
    for i, block in ipairs(el.content) do
      if block.t == "Header" and i == 1 then
        title = pandoc.utils.stringify(block)
      else
        body:insert(block)
      end
    end
    local html = string.format(
      [[<div class="abstract page-break">
  <div class="abstract-title">%s</div>
  %s
</div>]],
      title,
      pandoc.write(pandoc.Pandoc(body), "html")
    )
    return pandoc.RawBlock("html", html)
  end

  if el.classes:includes("figure") then
    local caption = read_attr(el, "caption") or ""
    local body = pandoc.write(pandoc.Pandoc(el.content), "html")
    local cap = caption ~= "" and ('<figcaption class="figure-caption">' .. caption .. "</figcaption>") or ""
    return pandoc.RawBlock("html", '<figure class="figure">' .. body .. cap .. "</figure>")
  end

  if el.classes:includes("equation") then
    local label = read_attr(el, "label") or ""
    local body = pandoc.write(pandoc.Pandoc(el.content), "html")
    local lbl = label ~= "" and ('<span class="equation-label">(' .. label .. ")</span>") or ""
    return pandoc.RawBlock("html", '<div class="equation-block">' .. body .. lbl .. "</div>")
  end

  return nil
end

function Header(el)
  if el.classes:includes("section-header") then
    local label = read_attr(el, "label") or ""
    local title = pandoc.utils.stringify(el)
    local html = string.format(
      [[<div class="academic-section">
  <div class="academic-number">%s</div>
  <h2 class="academic-title">%s</h2>
</div>]],
      label,
      title
    )
    el.classes:insert("academic-toc-source")
    return { el, pandoc.RawBlock("html", html) }
  end
  return nil
end
