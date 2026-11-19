"""#42 원자료: 119 구급 운영 현황(KOSIS 156 TX_15602_A018), 구조활동 총괄(TX_15602_A004).
순직·공상자는 소방청 hwp 문서(공공데이터포털 15131241)라 parse_hwp.py가 따로 읽는다."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kosis")); import kosis_curl as k
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
ys = ",".join(str(y) for y in range(2025, 2015, -1))
k.fetch("156", "TX_15602_A018", f"Y,{ys},@", os.path.join(R, "ems.json"), items=["16001", "16002", "16003"])
k.fetch("156", "TX_15602_A004", f"Y,{ys},@", os.path.join(R, "rescue.json"))
for f in ("ems.json", "rescue.json"):
    r = k.table(os.path.join(R, f)); print(f, len(r))
    for x in r[:6]: print("  ", x[:14])
