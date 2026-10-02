"""ZIP+XML 기반 문서(HWPX, DOCX)에서 문단 텍스트를 뽑는다."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from lxml import etree

_SECTION_RE = re.compile(r"^Contents/section(\d+)\.xml$")


def extract_hwpx_text(path: Path | str) -> str:
    with zipfile.ZipFile(path) as z:
        sections = sorted(
            (n for n in z.namelist() if _SECTION_RE.match(n)),
            key=lambda n: int(_SECTION_RE.match(n).group(1)),
        )
        paragraphs: list[str] = []
        for name in sections:
            paragraphs.extend(_paragraphs(z.read(name)))
    return "\n".join(paragraphs)


def extract_docx_text(path: Path | str) -> str:
    with zipfile.ZipFile(path) as z:
        return "\n".join(_paragraphs(z.read("word/document.xml")))


def _local(el) -> str:
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def _paragraphs(xml: bytes) -> list[str]:
    """<p> 단위로 그 문단에 직접 속한 <t> 텍스트만 모은다.

    표 셀 안의 문단은 바깥 문단의 자손이기도 하므로, 가장 가까운 <p> 조상이
    자기 자신인 <t>만 취해야 같은 글이 두 번 들어가지 않는다.
    """
    root = etree.fromstring(xml)
    out: list[str] = []
    for p in root.iter("{*}p"):
        parts: list[str] = []
        for t in p.iter("{*}t"):
            anc = t.getparent()
            while anc is not None and _local(anc) != "p":
                anc = anc.getparent()
            if anc is p:
                parts.append("".join(t.itertext()))
        line = "".join(parts).strip()
        if line:
            out.append(line)
    return out
