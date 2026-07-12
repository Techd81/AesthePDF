-- Whitepaper: lead, pullquote, stats, insight

function Div(el)
  if el.classes:includes("lead") then
    return pandoc.RawBlock(
      "html",
      '<div class="lead">' .. pandoc.write(pandoc.Pandoc(el.content), "html") .. "</div>"
    )
  end

  if el.classes:includes("pullquote") then
    return pandoc.RawBlock(
      "html",
      '<blockquote class="pullquote">' .. pandoc.utils.stringify(el.content) .. "</blockquote>"
    )
  end

  if el.classes:includes("stats") then
    local items = {}
    for _, block in ipairs(el.content) do
      local text = pandoc.utils.stringify(block)
      local value, label = text:match("^(.-)|(.+)$")
      if value and label then
        table.insert(
          items,
          '<div class="stat-item"><div class="stat-value">' .. value .. '</div><div class="stat-label">' .. label .. "</div></div>"
        )
      end
    end
    return pandoc.RawBlock("html", '<div class="stats-grid">' .. table.concat(items, "") .. "</div>")
  end

  if el.classes:includes("insight") then
    local title_text = nil
    local body = pandoc.List()
    for _, block in ipairs(el.content) do
      if block.t == "Header" and not title_text then
        title_text = pandoc.utils.stringify(block)
      else
        body:insert(block)
      end
    end
    local title_html = title_text and ('<div class="insight-title">' .. title_text .. "</div>") or ""
    return pandoc.RawBlock(
      "html",
      '<div class="insight">' .. title_html .. pandoc.write(pandoc.Pandoc(body), "html") .. "</div>"
    )
  end

  return nil
end

function Header(el)
  if el.classes:includes("section-header") then
    local label = el.attributes["label"] or el.attributes["data-label"] or ""
    local title = pandoc.utils.stringify(el)
    local html = string.format(
      [[<div class="wp-section">
  <div class="wp-chapter">%s</div>
  <h2 class="wp-title" id="%s">%s</h2>
  <div class="wp-divider"></div>
</div>]],
      label,
      el.identifier or "",
      title
    )
    el.classes:insert("wp-toc-source")
    return { el, pandoc.RawBlock("html", html) }
  end
  return nil
end
