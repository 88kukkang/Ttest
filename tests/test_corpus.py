from moisdb.corpus import clean_text, compose_text, select_attachment_texts

BODY = "\n".join([
    "□ 행정안전부는 2026년도 지방소멸대응기금 배분 결과를 발표했다.",
    "○ 이번 배분은 기초자치단체 89곳과 관심지역 18곳을 대상으로 한다.",
    "○ 평가는 외부 전문가로 구성된 평가위원회가 진행하였다.",
    "○ 생활인구 유입 효과를 중점적으로 살폈다고 설명하였다.",
])


def test_clean_text_removes_boilerplate_and_contacts():
    raw = "\n".join([
        "보도시점 2025. 6. 10.(화) 12:00",
        "배포 2025. 6. 9.(월)",
        "□ 지방소멸대응기금 배분 결과 발표 (문의 044-205-1234, moi@korea.kr)",
        "담당 부서 지역균형발전과",
        "과장 홍길동",
        "사무관 김철수",
        "- 3 -",
        "<끝>",
    ])
    assert clean_text(raw) == "□ 지방소멸대응기금 배분 결과 발표 (문의 , )"


def test_select_attachment_texts_dedupes_same_document_formats():
    atts = [
        {"seq": 1, "filename": "250610 (보도자료) 기금 배분.hwpx", "local_path": None, "file_type": "hwpx", "text": "HWPX"},
        {"seq": 2, "filename": "250610 (보도자료) 기금 배분.pdf", "local_path": None, "file_type": "pdf", "text": "PDF"},
        {"seq": 3, "filename": "(붙임) 배분액.hwp", "local_path": None, "file_type": "hwp", "text": "붙임"},
        {"seq": 4, "filename": "사진.jpg", "local_path": None, "file_type": "image", "text": None},
    ]
    assert select_attachment_texts(atts) == ["HWPX", "붙임"]


def test_compose_prefers_attachment_when_it_contains_body():
    att = "보도자료 머리말\n" + BODY + "\n붙임 표"
    assert compose_text(BODY, [att]) == (att, "attachments")


def test_compose_uses_attachment_when_body_is_stub():
    assert compose_text("첨부파일을 참고하시기 바랍니다.", ["첨부 본문"]) == ("첨부 본문", "attachments")


def test_compose_concatenates_when_contents_differ():
    text, label = compose_text(BODY, ["시군구별 배분액 표"])
    assert label == "body+attachments"
    assert text.startswith(BODY) and text.endswith("시군구별 배분액 표")


def test_compose_modes():
    assert compose_text(BODY, ["첨부"], mode="body") == (BODY, "body")
    assert compose_text(BODY, ["첨부"], mode="attachments") == ("첨부", "attachments")
    assert compose_text(BODY, []) == (BODY, "body")


def test_clean_text_drops_contact_table_but_keeps_appendix():
    raw = "\n".join([
        "□ 행정안전부는 민원 혁신 사례보고회를 개최한다.",
        "담당 부서",
        "행정안전부",
        "민원제도과",
        "책임자",
        "과 장",
        "김교열",
        "(044-205-2441)",
        "붙임",
        "5개 기관 민원해결 우수사례 발표 요약",
        "- 반복·특이민원에 대해 충분한 면담과 현장 확인을 통해 민원 발생 원인을 파악",
    ])
    assert clean_text(raw).splitlines() == [
        "□ 행정안전부는 민원 혁신 사례보고회를 개최한다.",
        "5개 기관 민원해결 우수사례 발표 요약",
        "- 반복·특이민원에 대해 충분한 면담과 현장 확인을 통해 민원 발생 원인을 파악",
    ]


def test_compose_uses_attachment_when_body_is_summary_pointing_to_it():
    # 실제 누리집 본문 형태: 두세 문장 요약 + '자세한 내용은 첨부를 참고' + 담당자
    body = "\n".join([
        "행정안전부(장관 윤호중)는 9월 11일(목)부터 9월 12일(금)까지 전북특별자치도 군산새만금컨벤션센터에서 "
        "'제42회 지역정보화 우수사례 발표대회'를 개최한다고 밝혔다.",
        "자세한 내용은 첨부를 참고하시기 바랍니다.",
        "* 담당자 : 지역디지털협력과 박찬수(044-205-2763)",
    ])
    att = "□ 행정안전부(장관 윤호중)는 9월 11일(목)부터 … ‘제42회 지역정보화 우수사례 발표대회’를 개최한다고 밝혔다."
    assert compose_text(body, [att]) == (att, "attachments")
    assert "담당자" not in clean_text(body)
