"""Kiwi 형태소 분석기로 명사(+붙여 쓴 복합명사)를 뽑는다.

예) '지방소멸대응기금 배분' → 지방, 소멸, 대응, 기금, 지방소멸대응기금, 배분
    단일 명사(빈도 집계용)와 띄어쓰기 없이 붙은 명사열(정책 용어 포착용)을 함께 낸다.
"""

from __future__ import annotations

import logging
import sqlite3
from importlib import resources
from pathlib import Path

from .. import db

log = logging.getLogger(__name__)

NOUN_TAGS = {"NNG", "NNP", "SL", "SH"}  # 일반명사, 고유명사, 외국어(AI 등), 한자
MERGE_SUFFIXES = {"화", "성", "력"}  # 활성+화, 안전+성, 경쟁+력 은 한 단어로 붙인다
MAX_COMPOUND_PARTS = 4


def _read_lines(path: Path | None, default_name: str) -> list[str]:
    if path is not None:
        text = Path(path).read_text(encoding="utf-8")
    else:
        text = resources.files("moisdb.resources").joinpath(default_name).read_text(encoding="utf-8")
    return [l.strip() for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]


class NounTokenizer:
    VERSION = "kiwi-nouns-v1"

    def __init__(
        self,
        userdict: Path | None = None,
        stopwords: Path | None = None,
        min_len: int = 2,
        compounds: bool = True,
    ):
        from kiwipiepy import Kiwi

        self.kiwi = Kiwi()
        self.min_len = min_len
        self.compounds = compounds
        user_words = _read_lines(userdict, "userdict.txt")
        for line in user_words:
            parts = line.split("\t")
            word = parts[0].strip()
            tag = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "NNP"
            score = float(parts[2]) if len(parts) > 2 and parts[2].strip() else 0.0
            self.kiwi.add_user_word(word, tag, score)
        self.stopwords = set(_read_lines(stopwords, "stopwords.txt"))
        # 사전·불용어가 바뀌면 재분석되도록 버전에 반영
        self.version = f"{self.VERSION}:{db.text_hash(chr(10).join(user_words + sorted(self.stopwords)))[:8]}"

    def _keep(self, form: str) -> bool:
        return len(form) >= self.min_len and form not in self.stopwords and not form.isdigit()

    def tokenize(self, text: str) -> list[str]:
        out: list[str] = []
        run: list[tuple[str, int]] = []  # (형태, 끝 위치)

        def flush() -> None:
            if self.compounds and 2 <= len(run) <= MAX_COMPOUND_PARTS:
                compound = "".join(f for f, _ in run)
                if self._keep(compound):
                    out.append(compound)
            run.clear()

        for line in text.splitlines():
            for tok in self.kiwi.tokenize(line):
                end = tok.start + tok.len
                attached = bool(run) and run[-1][1] == tok.start
                if tok.tag == "XSN" and tok.form in MERGE_SUFFIXES and attached:
                    form = run[-1][0] + tok.form
                    run[-1] = (form, end)
                    if out and out[-1] == form[:-1]:
                        out[-1] = form
                    elif self._keep(form):
                        out.append(form)
                    continue
                if tok.tag in NOUN_TAGS:
                    if not attached:
                        flush()
                    run.append((tok.form, end))
                    if self._keep(tok.form):
                        out.append(tok.form)
                else:
                    flush()
            flush()
        return out


def tokenize_corpus(conn: sqlite3.Connection, tokenizer: NounTokenizer, rebuild: bool = False) -> int:
    """doc_text 가 바뀌었거나 토크나이저 설정이 바뀐 문서만 다시 분석한다."""
    rows = conn.execute(
        """SELECT d.release_id, d.text, d.text_hash FROM doc_text d
           LEFT JOIN doc_tokens t ON t.release_id = d.release_id
           WHERE ? OR t.release_id IS NULL OR t.text_hash != d.text_hash OR t.tokenizer != ?""",
        (int(rebuild), tokenizer.version),
    ).fetchall()
    for i, row in enumerate(rows, start=1):
        tokens = tokenizer.tokenize(row["text"])
        conn.execute(
            """INSERT INTO doc_tokens (release_id, tokenizer, text_hash, tokens, built_at) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (release_id) DO UPDATE SET tokenizer = excluded.tokenizer, text_hash = excluded.text_hash,
                   tokens = excluded.tokens, built_at = excluded.built_at""",
            (row["release_id"], tokenizer.version, row["text_hash"], " ".join(tokens), db.now()),
        )
        if i % 200 == 0:
            conn.commit()
            log.info("[tokenize] %d/%d", i, len(rows))
    conn.commit()
    return len(rows)
