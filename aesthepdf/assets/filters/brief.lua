-- Brief: KPIs, timeline, action items

local function escape_html(text)
  return text
    :gsub("&", "&amp;")
    :gsub("<", "&lt;")
    :gsub(">", "&gt;")
    :gsub('"', "&quot;")
end

local function record_lines(el)
  local lines = {}

  local function append(inlines)
    local text = pandoc.utils.stringify(pandoc.Inlines(inlines))
    text = text:gsub("^%s+", ""):gsub("%s+$", "")
    if text ~= "" then
      table.insert(lines, text)
    end
  end

  for _, block in ipairs(el.content) do
    if block.t == "Para" or block.t == "Plain" then
      local current = pandoc.List()
      for _, inline in ipairs(block.content) do
        if inline.t == "SoftBreak" or inline.t == "LineBreak" then
          append(current)
          current = pandoc.List()
        else
          current:insert(inline)
        end
      end
      append(current)
    else
      local text = pandoc.utils.stringify(block)
      if text ~= "" then
        table.insert(lines, text)
      end
    end
  end

  return lines
end

function Div(el)
  if el.classes:includes("kpis") then
    local items = {}
    for _, text in ipairs(record_lines(el)) do
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
            escape_html(name),
            escape_html(value),
            delta_class,
            escape_html(delta)
          )
        )
      end
    end
    return pandoc.RawBlock("html", '<div class="kpi-row">' .. table.concat(items, "") .. "</div>")
  end

  if el.classes:includes("timeline") then
    local items = {}
    for _, text in ipairs(record_lines(el)) do
      local date, event = text:match("^(.-)|(.+)$")
      if date and event then
        table.insert(
          items,
          '<div class="timeline-item"><span class="timeline-date">' .. escape_html(date) .. '</span><span class="timeline-event">' .. escape_html(event) .. "</span></div>"
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
