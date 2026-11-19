"""#47 원자료: 한국행정연구원 사회통합실태조사 「기관별 신뢰 정도」(KOSIS 417 DT_417001_0038), 2013–2025년."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kosis")); import kosis_curl as k
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
m = k.meta("417", "DT_417001_0038"); t = k.tree("417", "DT_417001_0038")
for c, v in t.items(): print(c, [(x["itmId"], x["scrKor"]) for x in v])
A = [i["itmId"] for i in m["classInfoList"][0]["itmList"]] + [x["itmId"] for x in t.get("A", [])]
ys = ",".join(str(y) for y in range(2025, 2012, -1))
k.fetch("417", "DT_417001_0038", f"Y,{ys},@", os.path.join(R, "trust_all.json"), classes={"A": ["10"]})
k.fetch("417", "DT_417001_0038", "Y,2025,2024,2019,2013,@", os.path.join(R, "trust_groups.json"), classes={"A": A})
for f in ("trust_all.json", "trust_groups.json"):
    r = k.table(os.path.join(R, f)); print(f, len(r))
    for x in r[:8]: print("  ", x[:12])
