"""첨부파일 형식 판별과 형식별 텍스트 추출."""

from __future__ import annotations

import zipfile
from pathlib import Path

import olefile

from .html import html_to_text, normalize_lines
from .hwp import HwpError, extract_hwp_text
from .pdf import extract_pdf_text
from .xmlzip import extract_docx_text, extract_hwpx_text

# 텍스트를 뽑을 수 있는 문서 형식
TEXT_TYPES = ("hwpx", "hwp", "docx", "pdf")

__all__ = [
    "HwpError", "TEXT_TYPES", "extract_text", "html_to_text", "normalize_lines", "sniff_type",
]


def sniff_type(path: Path | str) -> str:
    """확장자 대신 파일 앞부분(매직 바이트)으로 형식을 판별한다."""
    path = Path(path)
    with path.open("rb") as f:
        head = f.read(16)
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        try:
            with olefile.OleFileIO(str(path)) as ole:
                if ole.exists("FileHeader"):
                    return "hwp"
        except OSError:
            pass
        return "ole"  # .doc/.xls 등
    if head.startswith(b"PK"):
        try:
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
        except zipfile.BadZipFile:
            return "unknown"
        if any(n.startswith("Contents/section") for n in names):
            return "hwpx"
        if "word/document.xml" in names:
            return "docx"
        return "zip"
    if head.startswith((b"\x89PNG", b"\xff\xd8\xff", b"GIF8")):
        return "image"
    if head.lstrip().lower().startswith((b"<!doctype", b"<html", b"<?xml")):
        return "html"  # 다운로드 대신 오류/안내 페이지가 온 경우
    return "unknown"


def extract_text(path: Path | str, file_type: str) -> str:
    if file_type == "hwp":
        text = extract_hwp_text(path)
    elif file_type == "hwpx":
        text = extract_hwpx_text(path)
    elif file_type == "docx":
        text = extract_docx_text(path)
    elif file_type == "pdf":
        text = extract_pdf_text(path)
    else:
        raise ValueError(f"텍스트 추출 미지원 형식: {file_type}")
    return normalize_lines(text)
