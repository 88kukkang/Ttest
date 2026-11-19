"""Fetch the parental leave statistics (육아휴직통계, KOSIS 101 DT_CC2024*) into raw/. usage: python3 fetch.py <rawdir>"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kosis"))
import kosis_curl as K
raw = sys.argv[1]; os.makedirs(raw, exist_ok=True)
Y = "Y," + ",".join(str(y) for y in range(2010, 2025)) + ",@"
for t in ["A001", "A002", "A003", "A004", "A005", "B001", "B002", "B003", "B004", "B005", "C001", "C002", "C003", "C004", "C005", "D001", "D002", "D003", "D004", "A006", "A007", "A008", "E001", "E002", "F001"]:
    tbl = "DT_CC2024" + t
    try:
        d = K.meta("101", tbl); K.fetch("101", tbl, Y, os.path.join(raw, f"{t}.json")); print(t, d["tblNm"], d.get("containPeriod"), flush=True)
    except Exception as e: print(t, "skip", str(e)[:60], flush=True)
