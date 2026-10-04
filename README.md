# NBA 시즌 레이스

경기가 하나씩 진행될 때마다 팀의 **승률**과 **순위**가 어떻게 변했는지 꺾은선 그래프로 비교하는 인터랙티브 페이지입니다.
결과물은 `docs/index.html` 한 파일이고, 브라우저로 바로 열면 됩니다 (그래프는 Plotly.js).

## 기능

| 옵션 | 선택지 |
|---|---|
| 지표 | 승률 / 순위 |
| 승률 계산 | 시즌 누적 승률 / 최근 10경기 승률 |
| 순위 기준 | 컨퍼런스 순위 (플레이오프 1–6위·플레이인 7–10위 구간 표시) / 리그 전체 순위 |
| 보기 | 한 차트에 겹쳐 보기 / 팀별로 나눠 보기 |
| 비교 | 지난 시즌 같은 경기 시점과 비교 (점선) |
| 배경 | 선택하지 않은 나머지 팀을 흐린 선으로 표시 |

- 팀은 최대 8개까지 고를 수 있고, 색은 팀에 고정됩니다 (다른 팀을 빼도 색이 바뀌지 않음).
- `서부 1–4위`, `작년보다 많이 오른 4팀` 같은 빠른 선택 버튼이 있습니다.
- 마우스를 올리면 그 경기 시점의 모든 팀 값, 전적, 상대, 점수가 함께 나옵니다.
- 아래 성적표에는 최종 전적, 승률, 순위, 지난 시즌 대비 승수 변화, 경기별 승패 막대가 있고, 그래프 값을 경기별 표로도 볼 수 있습니다.

## 실행

```bash
pip install -r requirements.txt
python -m nba_trend.build                 # 2025-26 시즌 + 2024-25 비교 → docs/index.html
```

옵션:

```bash
python -m nba_trend.build --season 2027               # 2026-27 시즌 (진행 중이어도 됨)
python -m nba_trend.build --compare none              # 지난 시즌 비교 없이
python -m nba_trend.build --source bbref --refresh    # basketball-reference에서 다시 수집
```

`--season` 은 basketball-reference 관례대로 시즌이 끝나는 해입니다 (2026 = 2025-26).

## 데이터

- 기본 소스는 basketball-reference.com 의 시즌 일정 페이지(`NBA_2026_games-<월>.html`)입니다.
  요청 사이에 3.5초씩 쉬어서 사이트의 분당 요청 제한을 지킵니다.
- basketball-reference에 접속하지 못하면 GitHub에 공개된 [sportsdataverse](https://github.com/sportsdataverse/sportsdataverse-data) ESPN 박스스코어로 자동 전환합니다.
- 정리된 경기 결과는 `data/games_<시즌>.csv` 에 저장되고 다음 실행부터 재사용됩니다. 새로 받으려면 `--refresh`.
- 정규시즌 기록에 포함되지 않는 NBA컵 결승, 올스타전, 플레이인은 제외합니다.
- 순위는 각 날짜의 모든 경기가 끝난 뒤 기준입니다. 동률은 승률 → 승패 차 → 상대 전적 → 컨퍼런스 승률 → 득실차 순으로 단순하게 가리므로 공식 시드와 다를 수 있습니다.

> 현재 커밋된 `data/`와 `docs/index.html`은 sportsdataverse 데이터로 만들었습니다 (작업 환경에서 basketball-reference 접속이 막혀 있었음).
> 2024-25 최종 전적은 30개 팀 모두 basketball-reference 기록과 일치합니다.
> 로컬에서 `python -m nba_trend.build --source bbref --refresh` 로 basketball-reference 데이터로 다시 만들 수 있습니다.

## 구조

```
nba_trend/
  sources.py     경기 결과 수집 (bbref, sportsdataverse) 과 정규시즌 정리
  standings.py   팀별 경기 로그, 날짜별 컨퍼런스/리그 순위 계산
  teams.py       30개 팀 이름·약어·컨퍼런스
  template.html  페이지 (Plotly.js), 빌드 때 데이터가 들어감
  build.py       CLI
tests/           파서·정리·순위 계산 테스트 (python -m unittest discover -s tests)
```
