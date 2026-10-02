"""HWP 5.x(바이너리, OLE) 문서에서 본문 텍스트를 뽑는다.

구조: OLE 컨테이너 안의 BodyText/Section{n} 스트림(대개 raw deflate 압축)에
레코드가 연속으로 들어 있고, 그중 HWPTAG_PARA_TEXT(67) 레코드가 문단 텍스트(UTF-16LE)다.
표 안의 셀 문단도 같은 레코드로 들어 있으므로 순서대로 읽으면 표 내용까지 포함된다.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Iterator

import olefile

HWPTAG_PARA_TEXT = 67

# 1 WCHAR 크기의 문자 제어 코드. 나머지 0~31 코드는 인라인/확장 제어로 8 WCHAR(16바이트)를 차지한다.
_CHAR_CONTROLS = {0, 10, 13, 24, 25, 26, 27, 28, 29, 30, 31}


class HwpError(Exception):
    pass


def extract_hwp_text(path: Path | str) -> str:
    with olefile.OleFileIO(str(path)) as ole:
        if not ole.exists("FileHeader"):
            raise HwpError("HWP FileHeader 스트림이 없음")
        header = ole.openstream("FileHeader").read()
        flags = struct.unpack_from("<I", header, 36)[0]
        if flags & 0x2:
            raise HwpError("암호가 걸린 HWP 문서")
        if flags & 0x4:
            raise HwpError("배포용 HWP 문서(본문 암호화) — 같은 내용의 PDF/HWPX 첨부를 사용")
        compressed = bool(flags & 0x1)
        sections = sorted(
            (e for e in ole.listdir() if len(e) == 2 and e[0] == "BodyText" and e[1].startswith("Section")),
            key=lambda e: int(e[1][len("Section"):] or 0),
        )
        paragraphs: list[str] = []
        for entry in sections:
            data = ole.openstream(entry).read()
            if compressed:
                data = zlib.decompress(data, -15)
            paragraphs.extend(iter_para_texts(data))
    return "\n".join(p for p in paragraphs if p.strip())


def iter_para_texts(data: bytes) -> Iterator[str]:
    """섹션 스트림의 레코드를 순회하며 문단 텍스트를 돌려준다."""
    pos, n = 0, len(data)
    while pos + 4 <= n:
        header = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        tag = header & 0x3FF
        size = (header >> 20) & 0xFFF
        if size == 0xFFF:
            size = struct.unpack_from("<I", data, pos)[0]
            pos += 4
        payload = data[pos:pos + size]
        pos += size
        if tag == HWPTAG_PARA_TEXT:
            yield decode_para_text(payload)


def decode_para_text(payload: bytes) -> str:
    out = bytearray()
    i, n = 0, len(payload) // 2
    while i < n:
        code = struct.unpack_from("<H", payload, i * 2)[0]
        if code >= 32:
            out += payload[i * 2:i * 2 + 2]
            i += 1
        elif code in _CHAR_CONTROLS:
            if code == 10:  # 줄바꿈
                out += "\n".encode("utf-16-le")
            elif code == 24:  # 하이픈
                out += "-".encode("utf-16-le")
            elif code in (30, 31):  # 묶음 빈칸, 고정폭 빈칸
                out += " ".encode("utf-16-le")
            i += 1
        else:
            if code == 9:  # 탭
                out += "\t".encode("utf-16-le")
            i += 8
    return out.decode("utf-16-le", errors="replace")
