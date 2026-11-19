"""Fetch item-level CPI (KOSIS 101 DT_1J22112, 2020=100, national) month by month into raw/. usage: python3 fetch.py <rawdir>"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kosis"))
import kosis_curl as K
raw = sys.argv[1]; os.makedirs(raw, exist_ok=True)
# The metadata lists only the six top groups; the 484 item codes were taken once from the request the KOSIS page itself sends.
import json
CODES = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cpi_codes.json")))
for y in range(2014, 2027):
    ms = [f"{y}{m:02d}" for m in range(1, 13) if (y, m) <= (2026, 10)]
    K.fetch("101", "DT_1J22112", "M," + ",".join(ms) + ",@", os.path.join(raw, f"cpi_{y}.json"), classes={"C": ["T10"], "I": CODES}); print("cpi", y, flush=True)
