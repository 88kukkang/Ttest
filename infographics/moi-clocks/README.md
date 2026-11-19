# 보도자료의 시계

행안부 보도자료 DB(브랜치 `claude/moi-press-release-database-ncgqwa`)로 만든 인포그래픽 세 장: 자연재난 계절 시계, 사회재난 심전도, 보도 시점 일주일 시계.

- `build.py`: 숫자를 만드는 스크립트. 입력은 DB 페이지의 `docs.b64.txt`를 풀어 둔 `../web/docs.bin`과 DB 저장소의 `dataset/attachments.csv`
- `data.json`: 페이지가 읽는 자료(빌드 결과에서 필요한 항목만)
- `clocks.html`: 페이지(아티팩트 조각 형식, `data.json`을 옆에 두고 연다)
