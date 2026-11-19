"""#48 원자료: 농림축산검역본부 행정구역별 반려동물 등록 개체 수(공공데이터포털 15125454, 2022년 말 누계; raw/에 둔다)와
분모로 쓸 주민등록인구(KOSIS 101 DT_1B040A3)·주민등록세대수(DT_1B040B3), 2022년 12월."""
import os, sys
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "raw")
sys.path.insert(0, os.path.join(H, "..", "kosis")); import kosis_curl as k
for tbl, item, tag in (("DT_1B040A3", "T20", "pop"), ("DT_1B040B3", None, "hh")):
    m = k.meta("101", tbl); t = k.tree("101", tbl); cid = m["classInfoList"][0]["classId"]
    if tag == "hh": print([(i["itmId"], i["scrKor"]) for i in m["itemInfo"]["itmList"]])
    for i in m["classInfoList"][0]["itmList"]:
        kids = [x["itmId"] for x in t[cid] if x["upItmId"] == i["itmId"]]
        try: k.fetch("101", tbl, "M,202212,@", os.path.join(R, f"{tag}_{i['itmId']}.json"), items=[item] if item else None, classes={cid: [i["itmId"]] + kids})
        except RuntimeError as e: print("건너뜀", i["scrKor"], str(e)[:50])
print(sorted(os.listdir(R)))
