"""web/src/ 조각과 reports/report_data.json 으로 통합 페이지 web/index.html 을 만든다.

    python ci/build_hub.py

페이지가 읽는 데이터 파일(docs.b64.txt, cloud.b64.txt)은 ci/build_web_data.py 가 만든다.
"""

from pathlib import Path

SRC = Path("web/src")
report = Path("reports/report_data.json").read_text(encoding="utf-8").strip()
scripts = ["3_core.js", "4_ai.js", "5_search.js", "6_cloud.js", "7_network.js", "8_report_tabs.js"]
html = (
    (SRC / "1_head.html").read_text(encoding="utf-8")
    + (SRC / "2_body.html").read_text(encoding="utf-8")
    + f'<script type="application/json" id="report-data">{report}</script>\n<script>\n'
    + "".join((SRC / s).read_text(encoding="utf-8") for s in scripts)
    + "</script>\n"
)
Path("web/index.html").write_text(html, encoding="utf-8")
print(f"web/index.html ({len(html.encode('utf-8')) / 1024:.0f} KB)")
