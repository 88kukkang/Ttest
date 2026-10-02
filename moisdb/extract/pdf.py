"""PDF 텍스트 추출 (PyMuPDF)."""

from __future__ import annotations

from pathlib import Path


def extract_pdf_text(path: Path | str) -> str:
    import pymupdf

    with pymupdf.open(str(path)) as doc:
        return "\n".join(page.get_text("text") for page in doc)
