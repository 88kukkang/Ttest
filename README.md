# moisdb — 행정안전부 보도자료 DB · 키워드 분석

이재명 정부 출범일(**2025-06-04**) 이후 행정안전부 보도자료를 **본문과 첨부(HWP/HWPX/PDF) 내용까지** 모아
SQLite 데이터베이스로 만들고, 키워드 빈도·추이·월별 이슈·연관어를 분석하는 도구.

```
행안부 누리집 보도자료 게시판 ─▶ 목록 → 상세(원본 HTML 저장) → 첨부 다운로드 → 텍스트 추출
                                    → 본문/첨부 중복 제거 + 서식 정제 → 형태소 분석(Kiwi) → 분석·검색·내보내기
정책브리핑 OpenAPI (선택) ────────▶ 누락 교차검증
```

설계 이유와 세부 규칙은 [`docs/DESIGN.md`](docs/DESIGN.md), Claude in Chrome 활용법은 [`docs/CHROME_RECON.md`](docs/CHROME_RECON.md).

## 설치

파이썬 3.10 이상. **한국 인터넷 환경의 내 PC에서 실행하는 것을 권장**한다(일부 정부 사이트는 해외 접속을 막는다).

```bash
git clone <이 저장소> && cd Ttest
python -m venv .venv
# 윈도우: .venv\Scripts\activate   /   맥·리눅스: source .venv/bin/activate
pip install -e ".[analysis]"
```

## 처음 실행 순서

```bash
# 0) 파서 점검 — 실제 페이지를 한 장씩 받아서 제대로 읽히는지 눈으로 확인 (가장 중요)
moisdb recon list
moisdb recon article <목록에서 본 nttId>

# 1) 시험 수집 — 20건만
moisdb collect --limit 20
moisdb stats

# 2) 전체 수집 — 끊겨도 같은 명령을 다시 실행하면 이어서 진행
moisdb collect

# 3) 이후 정기 갱신 — 새 글만
moisdb update
```

`collect` = `discover`(목록) → `fetch`(상세·첨부) → `extract`(첨부 텍스트) → `build-text`(분석용 텍스트) → `tokenize`(형태소).
각 단계를 따로 실행할 수도 있다. `moisdb <명령> -h` 로 옵션 확인.

## 분석

```bash
moisdb top -n 50                                    # 기간 전체 상위 키워드 (보도자료 수 기준)
moisdb top --start 2026-01-01 --dept 재난          # 기간·부서 필터
moisdb trend 소비쿠폰 지방소멸대응기금 --freq month  # 키워드 월별 추이
moisdb distinctive --csv out/monthly_issues.csv     # 월별 '그 달에 유독 많이 나온' 키워드 → 엑셀
moisdb cooccur AI                                   # 연관어
moisdb search "주민자치회"                          # 전문 검색
moisdb export --format csv --out out/mois_press.csv # 전체 내보내기 (엑셀·R·pandas 용)
```

분석 품질은 **불용어·사용자 사전**이 좌우한다. `moisdb/resources/stopwords.txt`, `userdict.txt` 를 고친 뒤
`moisdb tokenize` 하면 바뀐 부분만 재분석된다.

## 데이터 위치

```
data/
  mois.sqlite3        DB (DB Browser for SQLite·엑셀·pandas 로 열람 가능)
  raw/mois/press/     상세 페이지 원본 HTML (파서 수정 후 moisdb reparse 로 재해석)
  files/mois/<nttId>/ 첨부 원본
```

## 코드 구조

```
moisdb/
  config.py               시작일, URL, 게시판 ID, 요청 간격
  http.py                 요청 간격·재시도·인코딩 처리
  db.py                   SQLite 스키마
  sources/mois_board.py   누리집 목록·상세·첨부 수집 및 파싱
  sources/korea_kr_api.py 정책브리핑 OpenAPI (보조)
  extract/                HWP·HWPX·PDF·DOCX·HTML 텍스트 추출
  corpus.py               본문/첨부 선택, 정제, 검색 색인
  analysis/tokenizer.py   Kiwi 명사·복합명사 추출
  analysis/keywords.py    빈도·추이·특징어(로그오즈비)·연관어
  cli.py                  명령줄
tests/                    합성 HTML·HWPX·PDF 로 전 과정을 오프라인 테스트 (pytest)
```

## GitHub Actions 로 수집하기 (PC 없이)

`ci/task.env` 의 `TASK=` 값을 바꿔 이 브랜치에 push 하면 `.github/workflows/moisdb-run.yml` 이 돈다.

| TASK | 하는 일 | 결과 |
|---|---|---|
| `recon` | 목록·상세·첨부 몇 건으로 파서 점검 | `samples/` |
| `collect` | 출범일 이후 전체 수집 → 추출 → 형태소 분석. 시간 제한(약 4.5시간)에 걸리면 다음 실행이 이어서 한다 | `dataset/`, `reports/stats.txt` |

- `dataset/mois_press.sqlite3.xz` — 분석용 DB (압축 해제 후 `moisdb --data-dir <폴더> build-text` 로 검색 색인 재생성)
- `dataset/mois_press.csv` — 보도자료 1건 = 1행 (엑셀)
- `dataset/attachments.csv` — 첨부 목록과 처리 상태
- 원본 HTML·첨부까지 포함한 전체 `data/` 는 실행 페이지의 Artifacts(`moisdb-data-full`, 30일 보관)

## 웹 페이지 (`web/`)

수집한 DB 로 만든 정적 페이지. 데이터 파일은 `python ci/build_web_data.py` 로 `web/` 에 만든다(저장소에는 올리지 않음).

| 파일 | 내용 | 데이터 |
|---|---|---|
| `web/search.html` | 보도자료 제목·본문 검색 (AND·"구절"·-제외, 기간·부서, 월별 분포, 결과 복사) | `docs.b64.txt` |
| `web/cloud.html` | 키워드 클라우드 (단어 수 50/100/200, 많이 나온 말·두드러진 말, 단어별 추이) | `cloud.b64.txt` |
| `web/network.html` | 키워드 관계도 (전체 관계망·중심어 연관어, 묶음 색, 연결별 보도자료) | `cloud.b64.txt` |
| `reports/keyword_report.html` | 첫 키워드 분석 보고서 (월별 특징어, 표기 변화, 주제 흐름) | 페이지 안에 포함 |

로컬에서 볼 때는 `cd web && python -m http.server` 후 브라우저로 연다(파일을 직접 열면 데이터 파일을 못 읽는다).

## 주의

- 사이트 구조는 2026-10-02 실제 페이지로 확인했다([DESIGN.md §7](docs/DESIGN.md#7-실제-사이트-확인-결과-2026-10-02-github-actions-정찰)). 개편되면 `recon` 부터 다시.
- 요청은 한 번에 하나씩, 간격 1.5초. 서버에 부담을 주지 않도록 더 낮추지 말 것.
- 행안부 누리집은 일부 해외(클라우드) IP 를 막는다. Actions 실행이 '접속할 수 없어 중단'으로 끝나면 다시 실행하면 된다(다른 러너가 배정됨).
- 등록일은 게시판 등록일 기준이다(보도 시점과 하루 정도 다를 수 있음).
