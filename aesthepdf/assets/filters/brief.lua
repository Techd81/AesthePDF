-- Brief: KPIs, timeline, action items

function Div(el)
  if el.classes:includes("kpis") then
    local items = {}
    for _, block in ipairs(el.content) do
      local text = pandoc.utils.stringify(block)
      local name, value, delta = text:match("^(.-)|(.-)|(.+)$")
      if name and value and delta then
        local delta_class = "neutral"
        if delta:match("^[+↑]") or delta:match("升") then
          delta_class = "up"
        elseif delta:match("^[-↓]") or delta:match("降") then
          delta_class = "down"
        end
        table.insert(
          items,
          string.format(
            '<div class="kpi-card"><div class="kpi-name">%s</div><div class="kpi-value">%s</div><div class="kpi-delta kpi-delta-%s">%s</div></div>',
            name,
            value,
            delta_class,
            delta
          )
        )
      end
    end
    return pandoc.RawBlock("html", '<div class="kpi-row">' .. table.concat(items, "") .. "</div>")
  end

  if el.classes:includes("timeline") then
    local items = {}
    for _, block in ipairs(el.content) do
      local text = pandoc.utils.stringify(block)
      local date, event = text:match("^(.-)|(.+)$")
      if date and event then
        table.insert(
          items,
          '<div class="timeline-item"><span class="timeline-date">' .. date .. '</span><span class="timeline-event">' .. event .. "</span></div>"
        )
      end
    end
    return pandoc.RawBlock("html", '<div class="timeline">' .. table.concat(items, "") .. "</div>")
  end

  if el.classes:includes("action") then
    local title_text = "待跟进"
    local body = pandoc.List(el.content)
    if #body > 0 and body[1].t == "Header" then
      title_text = pandoc.utils.stringify(body[1])
      body:remove(1)
    end
    return pandoc.RawBlock(
      "html",
      '<div class="action-box"><div class="action-title">' .. title_text .. "</div>" .. pandoc.write(pandoc.Pandoc(body), "html") .. "</div>"
    )
  end

  return nil
end

function Header(el)
  if el.classes:includes("section-header") then
    local title = pandoc.utils.stringify(el)
    local html = string.format('<h2 class="brief-section">%s</h2>', title)
    el.classes:insert("brief-toc-source")
    return { el, pandoc.RawBlock("html", html) }
  end
  return nil
end
