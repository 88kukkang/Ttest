import struct
import zlib

from conftest import make_hwpx, make_pdf

from moisdb.extract import extract_text, html_to_text, sniff_type
from moisdb.extract.hwp import HWPTAG_PARA_TEXT, decode_para_text, iter_para_texts


def _record(tag: int, payload: bytes) -> bytes:
    if len(payload) < 0xFFF:
        return struct.pack("<I", tag | (len(payload) << 20)) + payload
    return struct.pack("<I", tag | (0xFFF << 20)) + struct.pack("<I", len(payload)) + payload


def _wchars(*codes: int) -> bytes:
    return b"".join(struct.pack("<H", c) for c in codes)


def test_hwp_para_text_skips_inline_controls():
    # '가' + 확장 제어(표 등, 8 WCHAR) + '나' + 탭(인라인 8 WCHAR) + '다' + 문단끝
    payload = (
        "가".encode("utf-16-le")
        + _wchars(11, 0x6C74, 0x6262, 0, 0, 0, 0, 11)
        + "나".encode("utf-16-le")
        + _wchars(9, 0, 0, 0, 0, 0, 0, 9)
        + "다".encode("utf-16-le")
        + _wchars(13)
    )
    assert decode_para_text(payload) == "가나\t다"


def test_hwp_record_stream_including_long_record():
    long_text = "지방소멸" * 1200  # 0xFFF 바이트를 넘는 확장 길이 레코드
    stream = (
        _record(66, b"\x00" * 22)  # PARA_HEADER (무시)
        + _record(HWPTAG_PARA_TEXT, "행정안전부 보도자료".encode("utf-16-le") + _wchars(13))
        + _record(HWPTAG_PARA_TEXT, long_text.encode("utf-16-le"))
    )
    assert list(iter_para_texts(stream)) == ["행정안전부 보도자료", long_text]
    # 실제 HWP 는 raw deflate 로 압축되어 있다
    packed = zlib.compressobj(wbits=-15)
    compressed = packed.compress(stream) + packed.flush()
    assert list(iter_para_texts(zlib.decompress(compressed, -15)))[0] == "행정안전부 보도자료"


def test_hwpx_text_with_table_not_duplicated(tmp_path):
    path = tmp_path / "doc.hwpx"
    path.write_bytes(make_hwpx(["첫 문단", "둘째 문단"], table_cells=["셀A", "셀B"]))
    assert sniff_type(path) == "hwpx"
    text = extract_text(path, "hwpx")
    assert text.splitlines() == ["첫 문단", "둘째 문단", "셀A", "셀B"]


def test_pdf_text(tmp_path):
    path = tmp_path / "doc.pdf"
    path.write_bytes(make_pdf(["지방소멸대응기금 배분", "생활인구 유입"]))
    assert sniff_type(path) == "pdf"
    assert extract_text(path, "pdf") == "지방소멸대응기금 배분\n생활인구 유입"


def test_sniff_html_error_page(tmp_path):
    path = tmp_path / "x.hwp"
    path.write_bytes(b"  <!DOCTYPE html><html>error</html>")
    assert sniff_type(path) == "html"


def test_html_to_text_keeps_line_structure():
    html = "<div><p>첫 줄</p><p>둘째&nbsp;&nbsp;줄<br>셋째 줄</p><table><tr><td>가</td><td>나</td></tr></table></div>"
    assert html_to_text(html) == "첫 줄\n\n둘째 줄\n셋째 줄\n\n가 나"
