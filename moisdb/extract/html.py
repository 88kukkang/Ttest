"""HTML 조각을 줄바꿈이 살아 있는 평문으로 바꾼다."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

_BLOCK_TAGS = [
    "p", "div", "li", "tr", "table", "ul", "ol", "section", "article",
    "h1", "h2", "h3", "h4", "h5", "h6", "dd", "dt", "blockquote", "pre",
]
_SPACES_RE = re.compile(r"[ \t 　​]+")


def html_to_text(node: Tag | str) -> str:
    # 원본 트리를 건드리지 않도록 다시 파싱한 사본에서 작업한다.
    soup = BeautifulSoup(str(node), "lxml")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for cell in soup.find_all(["td", "th"]):
        cell.insert_after(" ")
    for block in soup.find_all(_BLOCK_TAGS):
        block.insert_before("\n")
        block.insert_after("\n")
    return normalize_lines(soup.get_text())


def normalize_lines(text: str) -> str:
    """줄 단위 공백 정리 + 연속 빈 줄을 하나로 줄인다."""
    lines = [_SPACES_RE.sub(" ", line).strip() for line in text.splitlines()]
    out: list[str] = []
    for line in lines:
        if line or (out and out[-1]):
            out.append(line)
    return "\n".join(out).strip()
