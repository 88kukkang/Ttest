import pytest

pytest.importorskip("kiwipiepy")

from moisdb.analysis.tokenizer import NounTokenizer  # noqa: E402


@pytest.fixture(scope="module")
def tok():
    return NounTokenizer()


def test_userdict_and_stopwords(tok):
    tokens = tok.tokenize("행정안전부는 2025년 지방소멸대응기금 배분 결과를 발표했다.")
    assert "지방소멸대응기금" in tokens  # 사용자 사전으로 한 단어 유지
    assert "행정안전부" not in tokens and "행정" not in tokens  # 불용어 처리
    assert "2025" not in tokens


def test_compound_nouns_and_suffix_merge(tok):
    tokens = tok.tokenize("재난안전관리체계 고도화와 AI기본법 시행")
    assert "재난안전관리체계" in tokens and "재난" in tokens
    assert "고도화" in tokens and "고도" not in tokens
    assert "AI기본법" in tokens


def test_custom_stopwords_change_version(tmp_path):
    sw = tmp_path / "sw.txt"
    sw.write_text("배분\n", encoding="utf-8")
    custom = NounTokenizer(stopwords=sw)
    assert "배분" not in custom.tokenize("지방소멸대응기금 배분")
    assert custom.version != NounTokenizer().version
