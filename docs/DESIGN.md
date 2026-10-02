# 행정안전부 보도자료 DB · 키워드 분석 설계

> 범위: 이재명 정부 출범일(**2025-06-04**) 이후 행정안전부 보도자료 전체, 본문과 첨부(HWP/HWPX/PDF) 내용 포함.
> 목표: 한 번 제대로 쌓아 두고 매일/매주 증분 갱신하며, 키워드 빈도·추이·특징어·연관어 분석을 반복할 수 있게 한다.

---

## 1. 데이터를 어디서 가져올까

| 원천 | 장점 | 단점 | 역할 |
|---|---|---|---|
| **행안부 누리집 보도자료 게시판**<br>`mois.go.kr … commonSelectBoardList.do?bbsId=BBSMSTR_000000000008` | 원문 그대로, **첨부 HWP/PDF 전체** 확보, 담당부서 정보 | HTML 스크래핑이라 사이트 개편에 취약 | **주 원천** |
| **정책브리핑 보도자료 OpenAPI**<br>(공공데이터포털, `apis.data.go.kr/1371000/pressReleaseService`) | 공식 API, 본문 HTML 이 구조화돼 옴, 스크래핑 아님 | 인증키 필요, 조회 기간 제한(며칠 단위), 첨부 원문은 별도 | **보조·누락 검증** |
| 정책브리핑 웹(korea.kr) | 전 부처 통합 | 누리집과 중복, 스크래핑 | 사용 안 함 |
| **Claude in Chrome** | 사람처럼 화면을 보고 조작, 구조 파악이 빠름 | 수천 건 반복에는 느리고 비싸며, 중간에 끊기면 이어서 하기 어려움 | **정찰(구조 확인)·예외 처리** |

**결론:** 대량 수집은 파이썬 스크립트(이 저장소)로 하고 — 내 PC 또는 GitHub Actions(아래 README 참고)에서 — Claude in Chrome 은 ① 처음에 사이트 구조를 확인하고
② 스크립트가 못 여는 페이지가 생겼을 때 들여다보는 용도로 쓴다. 정찰 절차는 [`CHROME_RECON.md`](CHROME_RECON.md).

규모 감각: 행안부는 보도자료를 거의 매일 여러 건 내므로 16개월이면 **수천 건**, 첨부까지 합치면 요청 수천~1만 회 정도로 예상한다.
요청 간격 1.5초 기준 **몇 시간이면 끝나고**, SQLite 한 파일로 충분하다(서버 DB 불필요).

---

## 2. 전체 흐름

```
 [목록 페이지]──discover──▶ releases(status=listed)
                               │
 [상세 페이지]──fetch────────▶ 원본 HTML 저장(data/raw) + 본문/메타 파싱 → releases(status=fetched)
                               │      └─ 첨부 링크 → attachments(pending) → 다운로드(data/files) → downloaded
                               │
 [첨부 파일]──extract────────▶ HWP/HWPX/PDF/DOCX 텍스트 → attachments.text (extracted)
                               │
           ──build-text─────▶ 본문 vs 첨부 중 하나 선택 + 서식·연락처 제거 → doc_text, doc_fts(검색 색인)
                               │
           ──tokenize───────▶ Kiwi 형태소 분석 → 명사/복합명사 → doc_tokens
                               │
           ──top / trend / distinctive / cooccur / search / export──▶ 표·CSV
```

설계 원칙

1. **받기(fetch)와 해석(parse)을 분리한다.** 원본 HTML·첨부는 디스크에 그대로 저장하고, 파서를 고치면
   `moisdb reparse` 로 네트워크 없이 다시 해석한다. 사이트에 다시 요청할 일이 줄어든다.
2. **모든 단계는 다시 돌려도 안전(idempotent)하다.** 상태(`status`) 칼럼으로 어디까지 했는지 기록하므로,
   중간에 끊겨도 같은 명령을 다시 실행하면 이어서 진행한다.
3. **서버에 예의를 지킨다.** 요청 간격 기본 1.5초, 일시 오류는 지수 백오프로 최대 4회 재시도.
4. **파서는 선택자에만 의존하지 않는다.** nttId 링크 패턴·라벨(등록일/담당부서)·본문 블록 추정 휴리스틱을
   함께 써서, 마크업이 조금 바뀌어도 바로 깨지지 않게 했다. 대신 첫 실행 전 `recon` 으로 꼭 확인한다.

---

## 3. DB 스키마 (SQLite, `data/mois.sqlite3`)

| 테이블 | 내용 | 주요 칼럼 |
|---|---|---|
| `releases` | 보도자료 1건 = 1행 | `source`(mois/korea_kr), `source_id`(nttId), `published_date`, `department`, `title`, `body_text`, `raw_path`, `status` |
| `attachments` | 첨부파일 | `filename`, `file_type`(매직바이트로 판별), `local_path`, `sha256`, `text`, `status` |
| `doc_text` | 분석용 최종 텍스트 | `text_source`(body / attachments / body+attachments), `text`, `text_hash` |
| `doc_tokens` | 형태소 분석 결과 | `tokens`(공백 구분), `tokenizer`(사전·불용어 버전), `text_hash` |
| `doc_fts` | 전문 검색 색인 | FTS5 trigram (한국어 부분 문자열 검색) |
| `v_releases` | 조회용 뷰 | 월, 부서, 텍스트 길이, 첨부 수 |

SQLite 파일은 DB Browser for SQLite, 엑셀(파워쿼리), pandas, R 에서 그대로 열 수 있다.

---

## 4. 본문 텍스트를 어떻게 고르나 (중복 방지)

보도자료는 **같은 내용이 게시판 본문, HWP, PDF에 세 번** 들어 있는 경우가 많다. 다 합치면 키워드 빈도가 부풀려진다.

1. 첨부 중 **파일 이름이 같고 형식만 다른 것**(…배분.hwpx / …배분.pdf)은 하나만 남긴다. 우선순위 `hwpx > hwp > docx > pdf`
   (HWP 계열이 표·줄바꿈이 덜 깨진다).
2. 게시판 본문의 문장들이 **절반 이상 첨부에 그대로 있으면** → 첨부만 사용.
3. 게시판 본문이 '첨부파일 참조' 수준으로 짧으면 → 첨부만 사용.
4. 그 외(본문과 첨부가 서로 다른 내용, 예: 본문 + 붙임 표) → 둘을 이어 붙임.
5. 정제: 보도시점·배포 줄, 담당부서/책임자/담당자 줄, 전화번호·이메일·URL, 쪽번호, `<끝>` 제거.

어떤 경우로 처리됐는지는 `doc_text.text_source` 에 남는다(`moisdb stats` 에서 확인). `--mode body|attachments` 로 강제할 수도 있다.

배포용(암호화) HWP 는 본문을 읽을 수 없으므로 같은 이름의 PDF/HWPX 가 있으면 그쪽이 자동으로 쓰인다.

---

## 5. 형태소 분석 (Kiwi)

- 분석기: [kiwipiepy](https://github.com/bab2min/kiwipiepy) — 설치가 쉽고(자바 불필요) 정확도가 좋다.
- 추출 대상: 일반명사(NNG), 고유명사(NNP), 외국어(SL, 예: AI), 한자(SH).
- **복합명사:** 띄어쓰기 없이 붙은 명사열은 한 덩어리로도 낸다.
  `재난안전관리체계` → `재난`, `안전`, `관리`, `체계`, **`재난안전관리체계`**
  `AI기본법` → `AI`, `기본법`, **`AI기본법`**
- `활성+화`, `안전+성`, `경쟁+력` 은 한 단어로 붙인다.
- **사용자 사전**(`moisdb/resources/userdict.txt`): `지방소멸대응기금`, `고향사랑기부제`, `소비쿠폰` 처럼 쪼개지면 안 되는 정책 용어.
- **불용어**(`moisdb/resources/stopwords.txt`): 기관명·서식 용어·시간 표현.
- 사전/불용어를 고치면 토크나이저 버전이 바뀌어 `moisdb tokenize` 가 **필요한 문서만 자동 재분석**한다.

사전·불용어 다듬기가 분석 품질을 가장 크게 좌우한다. `top` 결과를 보며 반복해서 고치는 것을 전제로 한다.

---

## 6. 분석 메뉴

빈도는 기본적으로 **문서 빈도**(그 단어가 나온 보도자료 수)를 쓴다. 한 보도자료에서 같은 단어가 30번 나와도 1건이다.

| 명령 | 질문 | 방법 |
|---|---|---|
| `top` | 기간 전체에서 가장 많이 다룬 단어는? | 문서 빈도 순위 (+총빈도) |
| `trend 단어…` | 이 단어는 언제 많이 나왔나? | 월/주/분기별 "그 기간 보도자료 중 언급 비율" |
| `distinctive` | 달마다 **그 달에 유독** 많이 나온 이슈는? | 그 달 vs 나머지 기간, 정보적 사전분포 로그오즈비(Monroe et al. 2008) z값 |
| `cooccur 단어` | 이 단어와 같이 언급되는 단어는? | 동시 출현 문서 수 × lift |
| `search 검색어` | 이 표현이 나온 보도자료는? | FTS5 trigram (2글자 이하는 LIKE) |
| `export` | 다른 도구로 분석하고 싶다 | CSV/JSONL (원문·정제문·토큰 포함) |

모든 분석 명령은 `--start/--end`(기간), `--dept`(담당부서), `--csv`(엑셀 저장)를 지원한다.

예시 질문 → 명령
- "출범 후 행안부가 가장 많이 다룬 주제" → `moisdb top -n 100`
- "소비쿠폰은 언제 집중적으로 나왔나" → `moisdb trend 소비쿠폰 민생회복 --freq week`
- "월별 이슈 키워드 표" → `moisdb distinctive --csv out/monthly_issues.csv`
- "재난 관련 부서의 키워드" → `moisdb top --dept 재난`
- "AI 와 같이 나오는 단어" → `moisdb cooccur AI`

---

## 7. 실제 사이트 확인 결과 (2026-10-02, GitHub Actions 정찰)

| 항목 | 확인된 구조 | 반영 |
|---|---|---|
| 목록 | `commonSelectBoardList.do?bbsId=BBSMSTR_000000000008&pageIndex=N`, 쪽당 10건, 열: 번호·제목·첨부·**작성자(=담당부서)**·등록일·조회수 | `parse_list()` 가 '작성자' 열을 부서로 읽음 |
| 목록의 함정 | 상단 메뉴에 다른 게시판 글 링크(`bbsId=BBSMSTR_000000000031&nttId=…`), 페이지 이동 `fn_egov_select_noticeList(1609)` | 이 게시판 글 링크만 인정 |
| 상세 | 제목 `h4.subject`, 메타 `div.table_info`(등록일·작성자·조회수), 본문 `div#desc_pc` (모바일용 `div#desc_mo` 에 같은 내용 중복) | 선택자 맨 앞에 추가 |
| 본문 속 주석 | 한글 편집기 JSON 이 HTML 주석으로 수십 KB 들어 있음 | 저장 전 주석 제거 |
| 첨부 | `div.fileList` 의 `/cmm/fms/FileDown.do?atchFileId=…&fileSn=N`, 대부분 **같은 문서의 .hwpx + .pdf** 한 쌍, '바로보기'는 `fn_fileMgCheck` | HWPX 만 받고 PDF 는 보류(HWPX 실패 시 PDF 로 대체) |
| 첨부 본문 서식 | 맨 앞 '보도자료/보도시점/배포', 끝에 칸마다 한 줄씩 풀린 연락처 표, 그 뒤 '붙임' | 연락처 표 구간만 제거, 붙임은 유지 |
| 정책브리핑 API | 아직 미확인 (인증키 필요) | — |

실제 페이지 사본은 `tests/fixtures/real/` 에 두고 회귀 테스트(`tests/test_real_pages.py`)로 계속 점검한다.
사이트가 개편되면 `moisdb recon` 으로 다시 확인하고 `moisdb/sources/mois_board.py` 의 선택자를 고친 뒤
`moisdb reparse` → `build-text` → `tokenize` 로 반영한다(재수집 불필요).

---

## 8. 다음 단계 (로드맵)

1. **수집 안정화** — recon 으로 선택자 확정, 첫 20건 시험 수집, 누락 검증(`kr-api` + `crosscheck`).
2. **사전 다듬기** — `top -n 300` 을 보며 불용어/사용자 사전 보강. 동의어 묶기(예: `지자체`↔`지방자치단체`) 테이블 추가.
3. **게시판 확장** — 설명자료(해명자료) 게시판, 장관 동정 등 `config.BOARDS` 에 추가.
4. **토픽 분석** — BERTopic 또는 LDA 로 주제 군집, 월별 주제 비중.
5. **LLM 보강** — Claude API 로 보도자료마다 정책 분야 분류·한 줄 요약·핵심 정책어 추출 → `releases` 옆 테이블에 저장.
6. **시각화** — 월별 특징어 히트맵, 키워드 추이 그래프, 연관어 네트워크를 대시보드(Streamlit 또는 HTML 페이지)로.
7. **정기 실행** — 작업 스케줄러(윈도우)나 cron 으로 `moisdb update` 를 매일 실행.
