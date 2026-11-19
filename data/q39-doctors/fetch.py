"""#39 원자료 받기: 건강보험심사평가원 시군구별 의료인력현황(KOSIS 354 DT_HIRA4T) + 주민등록인구(KOSIS 101 DT_1B040A3).
시군구 이름이 시도마다 겹치므로(중구·동구…) 시도 하나씩 따로 받는다."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kosis"))
import kosis_curl as k
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "raw")
RC = "1535413101140072HC3"; JC = "1535413101140072B02"
m = k.meta("354", "DT_HIRA4T"); t = k.tree("354", "DT_HIRA4T")
sido = [(i["itmId"], i["scrKor"]) for i in m["classInfoList"][0]["itmList"]]
doc = ["1535413102140072B02.1"] + [i["itmId"] for i in t[JC] if i["upItmId"].endswith("B02.1")]
QS = "Q,202602,202504,202404,202401,202304,201904,201404,200904,@"
for sid, nm in sido:
    kids = [i["itmId"] for i in t[RC] if i["upItmId"] == sid]
    k.fetch("354", "DT_HIRA4T", QS, os.path.join(R, f"doc_{sid[-2:]}.json"), classes={RC: [sid] + kids, JC: doc}); print(nm, len(kids))
qs = [f"{y}0{n}" for y in range(2019, 2027) for n in range(1, 5)]; qs = [q for q in qs if "201904" <= q <= "202602"]
k.fetch("354", "DT_HIRA4T", "Q," + ",".join(reversed(qs)) + ",@", os.path.join(R, "doc_sido_q.json"), classes={RC: [s for s, _ in sido], JC: doc})
# 주민등록인구: 같은 시점
pm = k.meta("101", "DT_1B040A3"); pt = k.tree("101", "DT_1B040A3")
json.dump(pt, open(os.path.join(R, "pop_tree.json"), "w", encoding="utf-8"), ensure_ascii=False)
for i in pm["classInfoList"][0]["itmList"]:
    kids = [x["itmId"] for x in pt["A"] if x["upItmId"] == i["itmId"]]
    try: k.fetch("101", "DT_1B040A3", "M,202606,202512,202412,202403,202312,201912,201412,@", os.path.join(R, f"pop_{i['itmId']}.json"), items=["T20"], classes={"A": [i["itmId"]] + kids}); print(i["scrKor"], len(kids))
    except RuntimeError as e: print("자료 없음(새 통합시 코드):", i["scrKor"], str(e)[:60])
# 시군구 × 전문과목 전문의 (DT_HIRA4S), 2026년 2분기
SC = "1535413101140071HC3"; sm = k.meta("354", "DT_HIRA4S"); st = k.tree("354", "DT_HIRA4S")
for i in sm["classInfoList"][0]["itmList"]:
    kids = [x["itmId"] for x in st[SC] if x["upItmId"] == i["itmId"]]
    k.fetch("354", "DT_HIRA4S", "Q,202602,@", os.path.join(R, f"spec_{i['itmId'][-2:]}.json"), classes={SC: [i["itmId"]] + kids}); print("spec", i["scrKor"], len(kids))
