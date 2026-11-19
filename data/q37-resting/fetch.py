"""Fetch 'resting' (쉬었음) data from KOSIS 101 into raw/. usage: python3 fetch.py <rawdir>
DT_1DA7147S resting by age (monthly) · DT_1DA7002S population/employed/unemployed/inactive by age (monthly)
DT_1DA7145S inactive by sex and activity (monthly) · DT_1DE5052S reasons by age (Aug 2022-) · DT_1DE5011S reasons by sex (Aug 2016-)"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kosis"))
import kosis_curl as K
raw = sys.argv[1]; os.makedirs(raw, exist_ok=True)
def months(y): return [f"{y}{m:02d}" for m in range(1, 13) if (y, m) <= (2026, 10)]
for y in range(2003, 2027):
    p = "M," + ",".join(months(y)) + ",@"
    K.fetch("101", "DT_1DA7147S", p, os.path.join(raw, f"rest_{y}.json"))
    K.fetch("101", "DT_1DA7002S", p, os.path.join(raw, f"pop_{y}.json"), items=["T10", "T30", "T40", "T50"])
    K.fetch("101", "DT_1DA7145S", p, os.path.join(raw, f"act_{y}.json")); print(y, flush=True)
K.fetch("101", "DT_1DE5052S", "M," + ",".join(f"{y}08" for y in range(2022, 2027)) + ",@", os.path.join(raw, "why_age.json"))
K.fetch("101", "DT_1DE5011S", "M," + ",".join(f"{y}08" for y in range(2016, 2027)) + ",@", os.path.join(raw, "why_sex.json")); print("why")
