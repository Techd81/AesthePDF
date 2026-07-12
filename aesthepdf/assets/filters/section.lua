-- Shared: section headers, callouts, tags

local function read_attr(el, key)
  return el.attributes[key] or el.attributes["data-" .. key]
end

function Div(el)
  if el.classes:includes("callout") then
    local title_text = nil
    local body = pandoc.List()

    for _, block in ipairs(el.content) do
      if block.t == "Header" and not title_text then
        title_text = pandoc.utils.stringify(block)
      else
        body:insert(block)
      end
    end

    local parts = { '<div class="callout">' }
    if title_text then
      table.insert(parts, '<div class="callout-title">' .. title_text .. "</div>")
    end
    table.insert(parts, pandoc.write(pandoc.Pandoc(body), "html"))
    table.insert(parts, "</div>")
    return pandoc.RawBlock("html", table.concat(parts, "\n"))
  end

  if el.classes:includes("tags") then
    local tags = {}
    for _, block in ipairs(el.content) do
      local text = pandoc.utils.stringify(block):gsub("^%s+", ""):gsub("%s+$", "")
      for tag in text:gmatch("[^%s]+") do
        table.insert(tags, '<span class="tag">' .. tag .. "</span>")
      end
    end
    return pandoc.RawBlock("html", '<p class="tags">' .. table.concat(tags, "") .. "</p>")
  end

  return nil
end

function Header(el)
  if el.classes:includes("section-header") then
    local label = read_attr(el, "label") or ""
    el.attributes["data-label"] = label
    el.classes = { "section-header" }
    return el
  end
  return nil
end

function Span(el)
  if el.classes:includes("tag") then
    return pandoc.RawInline("html", '<span class="tag">' .. pandoc.utils.stringify(el) .. "</span>")
  end
  for _, cls in ipairs(el.classes) do
    if cls:match("^status%-") then
      return pandoc.RawInline("html", '<span class="status ' .. cls .. '">' .. pandoc.utils.stringify(el) .. "</span>")
    end
  end
  return nil
end
