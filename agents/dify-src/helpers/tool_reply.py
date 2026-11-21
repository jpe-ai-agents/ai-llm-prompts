def tool_rows(items):
    # Rows of a tool node's json output. The output is [{"data": []}] when the reply held no JSON.
    if items is None:
        return []
    if not isinstance(items, list):
        items = [items]
    return [item for item in items if item not in (None, "", [], {}, {"data": []})]


def tool_text(text, items):
    # One string for a tool reply. Dify fills `text` for a plain-text reply and `json` for a JSON reply, so use
    # whichever holds data. A JSON reply becomes a JSON array string, which the parsers read.
    text = "" if text is None else str(text)
    if text.strip():
        return text
    rows = tool_rows(items)
    return json.dumps(rows, ensure_ascii=False) if rows else ""


def tool_answer(text, items):
    # Plain text for the caller. A JSON reply becomes one line per item; a wrapped list is unwrapped first.
    text = "" if text is None else str(text)
    if text.strip():
        return text
    rows = []
    for item in tool_rows(items):
        wrapped = (item.get("tasks") or item.get("projects")) if isinstance(item, dict) else None
        if isinstance(wrapped, list):
            rows.extend(wrapped)
        else:
            rows.append(item)
    lines = []
    for item in rows:
        if isinstance(item, dict) and ("title" in item or "name" in item):
            status = "" if "done" not in item else (" - done" if item["done"] else " - open")
            lines.append(f"- ID {item.get('id', '')}: {item.get('title', item.get('name'))}{status}")
        else:
            lines.append(f"- {json.dumps(item, ensure_ascii=False)}")
    return "\n".join(lines)
