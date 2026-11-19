"""#44 원자료: 한국전력통계 행정구역별 용도별 판매전력량(KOSIS 310 DT_31002_A006, MWh)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kosis")); import kosis_curl as k
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
ys = ",".join(str(y) for y in range(2025, 2009, -1))
k.fetch("310", "DT_31002_A006", f"Y,{ys},@", os.path.join(R, "sales.json"), classes={"USE_1": ["01", "01_01", "01_02", "01_03", "01_04", "01_05", "01_06", "01_07", "01_07_17", "01_07_15", "01_07_11"]})
r = k.table(os.path.join(R, "sales.json")); print(len(r))
for x in r[:5]: print(x[:24])
