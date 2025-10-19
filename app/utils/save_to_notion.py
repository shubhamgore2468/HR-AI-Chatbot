import os, httpx
from typing import Dict, List, Any, Optional
import re
import json
from app.core.logger import log
from dotenv import load_dotenv
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")
NOTION_VERSION = os.getenv("NOTION_VERSION", "2022-06-28")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}" if NOTION_API_KEY else "",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

import re

def _rt_fragments(text: str):
    # inline code first
    parts = re.split(r"(`[^`]+`)", text)
    out = []
    def frag(t, bold=False, italic=False, code=False):
        return {"type":"text","text":{"content":t},
                "annotations":{"bold":bold,"italic":italic,"code":code}}
    for p in parts:
        if not p: 
            continue
        if p.startswith("`") and p.endswith("`"):
            out.append(frag(p[1:-1], code=True))
        else:
            # **bold** and *italic*
            i = 0
            for m in re.finditer(r"(\*\*[^*]+\*\*|\*[^*]+\*)", p):
                if m.start() > i:
                    out.append(frag(p[i:m.start()]))
                span = m.group(0)
                if span.startswith("**"):
                    out.append(frag(span[2:-2], bold=True))
                else:
                    out.append(frag(span[1:-1], italic=True))
                i = m.end()
            if i < len(p):
                out.append(frag(p[i:]))
    if not out:
        out = [{"type":"text","text":{"content":text}}]
    return out

def _rt(text: str):
    return _rt_fragments(text)

def _label_value(line: str):
    m = re.match(r"^\s*\*\*([^*]+):\*\*\s*(.*)$", line)
    if not m: return None
    label, val = m.group(1), m.group(2)
    return {
        "object":"block","type":"paragraph",
        "paragraph":{"rich_text":[
            {"type":"text","text":{"content":f"{label}: "},"annotations":{"bold":True}},
            *(_rt(val) if val else [])
        ]}
    }

def markdown_to_notion_blocks(markdown_text: str):
    lines = markdown_text.strip().split("\n")
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        # headings
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            text = m.group(2)
            if level == 1:
                blocks.append({"object":"block","type":"heading_1","heading_1":{"rich_text":_rt(text)}})
            elif level == 2:
                blocks.append({"object":"block","type":"heading_2","heading_2":{"rich_text":_rt(text)}})
            elif level == 3:
                blocks.append({"object":"block","type":"heading_3","heading_3":{"rich_text":_rt(text)}})
            else:
                # Notion only supports up to 3; make bold paragraph
                blocks.append({"object":"block","type":"paragraph","paragraph":{"rich_text":[
                    {"type":"text","text":{"content":text},"annotations":{"bold":True}}
                ]}})
            i += 1
            continue

        # bullets (-, *, +) and numbers
        m_b = re.match(r"^[-*+]\s+(.*)$", stripped)
        if m_b:
            content = m_b.group(1)
            blocks.append({"object":"block","type":"bulleted_list_item",
                           "bulleted_list_item":{"rich_text":_rt(content)}})
            i += 1
            continue

        m_n = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m_n:
            content = m_n.group(1)
            blocks.append({"object":"block","type":"numbered_list_item",
                           "numbered_list_item":{"rich_text":_rt(content)}})
            i += 1
            continue

        # **Label:** Value
        lv = _label_value(stripped)
        if lv:
            blocks.append(lv)
            i += 1
            continue

        # whole-line bold (**...**) → bold paragraph
        if stripped.startswith("**") and stripped.endswith("**") and len(stripped) > 4:
            blocks.append({"object":"block","type":"paragraph","paragraph":{"rich_text":[
                {"type":"text","text":{"content":stripped[2:-2]},"annotations":{"bold":True}}
            ]}})
            i += 1
            continue

        # fallback paragraph (with inline formatting)
        blocks.append({"object":"block","type":"paragraph","paragraph":{"rich_text":_rt(stripped)}})
        i += 1

    return blocks

def upload_to_notion(content: str | Dict[str, Any], *, page_id_or_url: str, title: str = "Job Description") -> Dict[str, Any]:
    """
    Appends blocks to a page using PATCH /v1/blocks/{page_id}/children
    (aligned to the official cURL you shared).
    """
    # page_id = _extract_notion_id(page_id_or_url)
    endpoint = f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children"

    # Build children just like your cURL example
    if isinstance(content, str):
        children = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": _rt(title)}
            },
            *markdown_to_notion_blocks(content)
        ]
    elif isinstance(content, dict):
        children = [
            {"object":"block","type":"heading_2","heading_2":{"rich_text": _rt(title)}},
            {"object":"block","type":"code","code":{
                "rich_text": [{"type":"text","text":{"content": json.dumps(content, ensure_ascii=False, indent=2)[:1950]}}],
                "language":"json"
            }},
        ]
    else:
        children = [{"object":"block","type":"paragraph","paragraph":{"rich_text": _rt(str(content))}}]

    with httpx.Client(timeout=20) as client:
        # IMPORTANT: use PATCH (matches the doc you pasted)
        resp = client.patch(endpoint, headers=HEADERS, json={"children": children})
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            # Bubble up Notion’s error body to make debugging easier
            raise RuntimeError(f"Notion error {resp.status_code}: {resp.text}") from e
        return resp.json()
