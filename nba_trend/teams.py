"""30개 팀 메타데이터와 데이터 소스별 약어/이름 매핑."""

# (표준 약어, 영문 이름, 한글 이름, 컨퍼런스, 기타 표기)
_TEAMS = [
    ("ATL", "Atlanta Hawks", "애틀랜타 호크스", "E", ()),
    ("BOS", "Boston Celtics", "보스턴 셀틱스", "E", ()),
    ("BKN", "Brooklyn Nets", "브루클린 네츠", "E", ("BRK",)),
    ("CHA", "Charlotte Hornets", "샬럿 호네츠", "E", ("CHO",)),
    ("CHI", "Chicago Bulls", "시카고 불스", "E", ()),
    ("CLE", "Cleveland Cavaliers", "클리블랜드 캐벌리어스", "E", ()),
    ("DET", "Detroit Pistons", "디트로이트 피스톤스", "E", ()),
    ("IND", "Indiana Pacers", "인디애나 페이서스", "E", ()),
    ("MIA", "Miami Heat", "마이애미 히트", "E", ()),
    ("MIL", "Milwaukee Bucks", "밀워키 벅스", "E", ()),
    ("NYK", "New York Knicks", "뉴욕 닉스", "E", ("NY",)),
    ("ORL", "Orlando Magic", "올랜도 매직", "E", ()),
    ("PHI", "Philadelphia 76ers", "필라델피아 76ers", "E", ()),
    ("TOR", "Toronto Raptors", "토론토 랩터스", "E", ()),
    ("WAS", "Washington Wizards", "워싱턴 위저즈", "E", ("WSH",)),
    ("DAL", "Dallas Mavericks", "댈러스 매버릭스", "W", ()),
    ("DEN", "Denver Nuggets", "덴버 너기츠", "W", ()),
    ("GSW", "Golden State Warriors", "골든스테이트 워리어스", "W", ("GS",)),
    ("HOU", "Houston Rockets", "휴스턴 로키츠", "W", ()),
    ("LAC", "Los Angeles Clippers", "LA 클리퍼스", "W", ("LA Clippers",)),
    ("LAL", "Los Angeles Lakers", "LA 레이커스", "W", ()),
    ("MEM", "Memphis Grizzlies", "멤피스 그리즐리스", "W", ()),
    ("MIN", "Minnesota Timberwolves", "미네소타 팀버울브스", "W", ()),
    ("NOP", "New Orleans Pelicans", "뉴올리언스 펠리컨스", "W", ("NO",)),
    ("OKC", "Oklahoma City Thunder", "오클라호마시티 썬더", "W", ()),
    ("PHX", "Phoenix Suns", "피닉스 선즈", "W", ("PHO",)),
    ("POR", "Portland Trail Blazers", "포틀랜드 트레일블레이저스", "W", ()),
    ("SAC", "Sacramento Kings", "새크라멘토 킹스", "W", ()),
    ("SAS", "San Antonio Spurs", "샌안토니오 스퍼스", "W", ("SA",)),
    ("UTA", "Utah Jazz", "유타 재즈", "W", ("UTAH",)),
]

TEAMS = {abbr: {"abbr": abbr, "name": name, "ko": ko, "conf": conf}
         for abbr, name, ko, conf, _ in _TEAMS}

_ALIASES = {}
for abbr, name, _ko, _conf, extra in _TEAMS:
    for key in (abbr, name, *extra):
        _ALIASES[key.upper()] = abbr


def normalize(team):
    """약어나 팀 이름을 표준 약어로 바꾼다. NBA 팀이 아니면(올스타 팀 등) None."""
    return _ALIASES.get(str(team).strip().upper())
