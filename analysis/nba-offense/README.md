# NBA 공격 50년 (1976-77 ~ 2025-26)

속도(페이스), 득점 효율, 선수 득점 분포, 한 선수에게 득점이 몰리는 정도, 시대 보정 비교.

- `fetch.py raw/`: Basketball-Reference에서 시즌별 표(리그 평균, 팀, 선수 경기당·100포제션당·고급)를 4.2초 간격으로 받는다. 받은 원본 HTML은 저장소에 넣지 않았다.
- `build.py`: 원본에서 `nba_data.json`을 만든다(`parse_util.py` 사용).
- `nba.html`: 페이지(아티팩트 조각 형식, `nba_data.json`을 옆에 두고 연다).

자료: Basketball-Reference.com (2026년 11월 수집). 페이스·공격 효율·사용률은 이 사이트의 추정치다.
