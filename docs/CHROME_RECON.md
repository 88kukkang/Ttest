# Claude in Chrome 으로 사이트 구조 확인하기

스크립트의 파서는 행안부 누리집 구조를 **추정해서** 만들었다. 실제 수집 전에 Claude in Chrome 으로 한 번 확인하면
선택자를 정확히 맞출 수 있다. 수천 건을 브라우저로 직접 긁는 건 느리고 중간에 끊기기 쉬우니, 대량 수집은 스크립트에 맡긴다.

## 1단계 — Claude in Chrome 에 붙여넣을 요청

```
행정안전부 보도자료 게시판 구조를 확인하려고 해. 아래 순서대로 해 줘. 페이지 내용을 바꾸거나 무언가를 제출하지는 마.

1. https://www.mois.go.kr/frt/bbs/type010/commonSelectBoardList.do?bbsId=BBSMSTR_000000000008 을 열어.
2. 목록 표의 열 이름을 순서대로 알려 줘 (예: 번호/제목/담당부서/등록일/조회/첨부).
3. 첫 3개 글 제목 링크의 href 와 onclick 속성 원문을 그대로 옮겨 줘.
4. 페이지 아래 '2' 페이지를 눌러 이동한 뒤 주소창 URL 을 알려 줘. (pageIndex 같은 파라미터가 붙는지)
5. 목록 맨 위에 고정된 공지 글이 있는지, 있다면 번호 칸에 무엇이 표시되는지 알려 줘.
6. 2025년 6월 4일 이후 글 중 첨부파일이 있는 글 하나를 열어서:
   a. 주소창 URL
   b. 제목 / 등록일 / 담당부서가 들어 있는 HTML 요소의 태그와 class (개발자 도구 요소 기준)
   c. 본문 텍스트를 감싸는 가장 바깥 요소의 태그·class·id
   d. 첨부파일 다운로드 링크의 href(또는 onclick) 원문, 그리고 '바로보기/미리보기' 링크가 따로 있는지
   e. 본문이 HTML 텍스트인지, 이미지(카드뉴스 등)인지
7. 위 결과를 표로 정리해 줘.
```

## 2단계 — 샘플 HTML 저장

목록 페이지와 위에서 연 상세 페이지에서 각각 `Ctrl+S` → 형식 "웹페이지, HTML만" 으로 저장한다
(예: `list.html`, `article.html`).

## 3단계 — 저장한 파일로 파서 점검 (네트워크 사용 안 함)

```bash
moisdb recon list --file list.html
moisdb recon article --file article.html
```

확인할 것
- 목록: `ntt_id`, `date`, `department` 가 모두 채워지는가? 고정 공지가 `pinned=True` 인가?
- 상세: 제목/등록일/담당부서가 맞는가? "본문 탐지"가 `heuristic` 이면 미리보기 본문에 메뉴·푸터가 섞이지 않았는가?
  첨부 목록에 실제 파일만 있고 '바로보기' 링크는 빠졌는가?

어긋나는 부분은 1단계에서 받은 태그·class 정보를 `moisdb/sources/mois_board.py` 의
`TITLE_SELECTORS` / `BODY_SELECTORS` 맨 앞에 추가하면 된다. 이 대화(Claude Code)에 1단계 결과표와 저장한 HTML 을 주면
선택자 수정과 테스트 추가까지 바로 해 줄 수 있다.

## 스크립트가 막힐 때

- `stats` 에서 첨부 `file_type=html` 이 많다 → 다운로드가 쿠키·리퍼러를 요구하는 경우. Claude in Chrome 으로 첨부 하나를
  눌러 실제 요청 URL(개발자 도구 Network 탭)을 확인한다.
- 목록이 0건으로 나온다 → 목록이 자바스크립트로 그려지는 경우. Chrome 에서 '페이지 소스 보기'(Ctrl+U)에 글 제목이 있는지 확인한다.
