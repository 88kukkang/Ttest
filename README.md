# 다행이 데스크톱 펫

작업 표시줄 위를 걸어다니는 도트 다람쥐 **다행이**예요. 오른쪽 클릭으로 알람을 맞춰 두면 시간이 됐을 때 말풍선으로 알려줘요.

![다행이 도트 스프라이트](dahaengi/preview.png)

## 바로 받기 (exe)

👉 **[Dahaengi.exe 다운로드](https://github.com/88kukkang/Ttest/releases/latest/download/Dahaengi.exe)**

받은 파일을 더블클릭하면 바로 실행돼요. 설치나 파이썬은 필요 없어요.
처음 실행할 때 "Windows의 PC 보호" 창이 뜨면 **추가 정보 → 실행**을 눌러 주세요. (서명되지 않은 개인 제작 프로그램이라 뜨는 경고예요.)

exe는 `dahaengi/` 폴더가 바뀌어 푸시될 때마다 GitHub Actions가 Windows에서 자동으로 빌드해서 [Releases](https://github.com/88kukkang/Ttest/releases)에 올려요.

## 소스로 실행하기 (Windows)

1. [Python 3](https://www.python.org/downloads/)을 설치해요. 설치할 때 **Add python.exe to PATH**를 체크해 주세요.
2. `dahaengi/run.bat`을 더블클릭해요. (또는 `pythonw dahaengi\dahaengi.py`)

추가 라이브러리는 필요 없어요. 파이썬 기본 tkinter만 써요.

### 내 PC에서 직접 exe 만들기

`dahaengi/build_exe.bat`을 더블클릭하면 `dahaengi/dist/Dahaengi.exe`가 만들어져요. 이 파일만 있으면 파이썬이 없는 PC에서도 실행돼요.

### 윈도우 시작할 때 자동 실행

`Win + R` → `shell:startup` 입력 → 열린 폴더에 `Dahaengi.exe`(또는 `run.bat`)의 바로가기를 넣어 두세요.

## 사용법

| 동작 | 설명 |
| --- | --- |
| 가만히 두기 | 작업 표시줄 위를 걸어다니다가 가끔 멈춰서 쉬어요 |
| 왼쪽 클릭 | 깡충 뛰어요. 말풍선이 떠 있으면 닫아요 |
| 왼쪽 드래그 | 들어서 옮길 수 있어요. 놓으면 아래로 떨어져요 |
| 창 위에 놓기 | 폴더·인터넷 창 위에 놓으면 창 윗변에 올라서서 그 위를 걸어요. 창을 옮기면 같이 따라가고, 창을 닫거나 최소화하거나 다른 창에 가려지면 떨어져요 |
| 오른쪽 클릭 | 메뉴: 알람 설정, 켜진 알람 목록, 가만히 있기, 종료 |

### 알람

- 최대 5개까지 설정할 수 있어요. 각 알람마다 **사용 / 시간 / 할 말 / 매일 반복**을 정해요.
- 시간이 되면 다행이가 신나서 뛰면서 말풍선으로 설정한 말을 해요. 말풍선은 클릭하면 닫히고, 1분 뒤 저절로 닫혀요.
- **매일 반복**을 끄면 한 번 울린 뒤 자동으로 꺼져요.
- **미리보기** 버튼으로 말풍선을 미리 볼 수 있어요.
- 설정은 `%APPDATA%\Dahaengi\alarms.json`에 저장돼요.

## 파일 구성

- `dahaengi/dahaengi.py` — 프로그램 본체 (창, 이동, 메뉴, 알람, 말풍선)
- `dahaengi/desktop.py` — 열려 있는 창 위치를 알아내는 부분 (창 위를 걷기)
- `dahaengi/sprites.py` — 다행이 도트 그림을 코드로 그리는 부분 (색은 파일 위쪽 팔레트에서 바꿀 수 있어요)

> 다행이는 행정안전부 캐릭터예요. 이 프로그램은 개인용으로 만든 팬아트 스타일 도트 그림을 써요.
