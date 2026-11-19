"""Q4: elderly living alone. Census 65+ one-person households (SGIS) by sigungu 2015-2024,
MOIS registered 65+ population (Dec) as the denominator, MoHW national 독거노인 by age 2010-2024."""
import csv, io, json, re, subprocess, collections

S = "/tmp/claude-0/-home-user/867911d4-434e-5c1c-a4fa-95438af19a83/scratchpad"
N = json.load(open("names.json"))
H = json.load(open("sgis_65_1p.json"))
G = json.load(open(f"{S}/geo/kor_mun.json"))
YEARS = list(range(2015, 2025))
SIDO = {k: v[0] for k, v in N.items() if len(k) == 2}
SHORT = {"11": "서울", "21": "부산", "22": "대구", "23": "인천", "24": "광주", "25": "대전", "26": "울산", "29": "세종", "31": "경기", "32": "강원", "33": "충북", "34": "충남", "35": "전북", "36": "전남", "37": "경북", "38": "경남", "39": "제주"}
key = lambda s: re.sub(r"\s", "", s)


def census_code(geo):
    if geo == "37310": return "22520"  # 군위군 moved to Daegu in 2023
    if geo == "23030": return "23090"  # 인천 남구 -> 미추홀구
    if int(geo[2:]) >= 310: return geo[:2] + str(int(geo[2:]) + 200)
    return geo


ALIAS = [("강원도", "강원특별자치도"), ("전라북도", "전북특별자치도"), ("인천광역시남구", "인천광역시미추홀구"), ("경상북도군위군", "대구광역시군위군")]


def mois(y):
    t = subprocess.run(["iconv", "-f", "cp949", "-t", "utf-8", f"popsg_{y}.csv"], capture_output=True).stdout.decode()
    R = list(csv.reader(io.StringIO(t))); h = R[0]
    old = [i for i, c in enumerate(h) if re.search(r"_(65~69|70~74|75~79|80~84|85~89|90~94|95~99|100세 이상)", c)]
    out = {}
    for r in R[1:]:
        m = re.match(r"(.*?)\s*\((\d{10})\)", r[0]); k = key(m.group(1))
        for a, b in ALIAS:
            if k.startswith(a): k = b + k[len(a):]
        out[k] = (int(r[1].replace(",", "")), sum(int(r[i].replace(",", "") or 0) for i in old))
    return out


MO = {y: mois(y) for y in YEARS}
units, miss = [], []
for u in G["units"]:
    c = census_code(u["code"]); s = c[:2]
    nm = N[c][0] if c in N else u["name"]
    k = key(SIDO[s] + nm)
    pop = []
    for y in YEARS:
        v = MO[y].get(k)
        if v is None and s == "29":
            v = MO[y].get("세종특별자치시")
        if v is None and c == "31050":  # 부천: city row
            v = MO[y].get(key(SIDO[s] + "부천시"))
        if v is None: miss.append((y, k)); v = (0, 0)
        pop.append(v[1])
    hh = [H[c][str(y)] for y in YEARS]
    units.append({"code": u["code"], "name": nm.replace(" ", ""), "sido": SHORT[s], "d": u["d"], "c": u["c"], "h": hh, "p": pop})
print("missing pop", sorted(set(m[1] for m in miss))[:20], len(miss))

sido = {}
for s, nm in SHORT.items():
    hh = [H[s][str(y)] for y in YEARS]
    pop = [MO[y][key(SIDO[s] if s != "29" else "세종특별자치시")][1] if key(SIDO[s]) in MO[y] else None for y in YEARS]
    if None in pop:
        alt = [a for a, b in ALIAS if b == SIDO[s]]
        pop = [MO[y].get(key(SIDO[s]), MO[y].get(key(alt[0]) if alt else "", (0, 0)))[1] for y in YEARS]
    sido[s] = {"name": nm, "h": hh, "p": pop}
nat_h = [sum(sido[s]["h"][i] for s in sido) for i in range(len(YEARS))]
nat_p = [sum(sido[s]["p"][i] for s in sido) for i in range(len(YEARS))]
# unit sums vs sido (census): check consistency
for s in sido:
    us = sum(u["h"][-1] for u in units if u["code"][:2] == s or (u["code"] == "37310" and s == "22"))
    if abs(us - sido[s]["h"][-1]) > 0: print("unit sum diff", s, us, sido[s]["h"][-1])
    ps = sum(u["p"][-1] for u in units if (u["code"][:2] == s and u["code"] != "37310") or (u["code"] == "37310" and s == "22"))
    if abs(ps - sido[s]["p"][-1]) > 0: print("pop sum diff", s, ps, sido[s]["p"][-1])

# MoHW register-based 독거노인, national by age 2010-2024
mo1 = list(csv.reader(io.StringIO(subprocess.run(["iconv", "-f", "cp949", "-t", "utf-8", "d_15127846.bin"], capture_output=True).stdout.decode())))
age = collections.defaultdict(dict)
for r in mo1[1:]:
    a = "85세이상" if r[1] in ("85-89세", "90세이상") else r[1]
    age[a][int(r[0])] = age[a].get(int(r[0]), 0) + int(r[2])
for r in list(csv.reader(open("u1.csv")))[1:]:
    for a, v in zip(["65-69세", "70-74세", "75-79세", "80-84세", "85세이상"], r[2:]):
        age[a][int(r[0])] = age[a].get(int(r[0]), 0) + int(v)
mohw = {a: [age[a][y] for y in range(2010, 2025)] for a in ["65-69세", "70-74세", "75-79세", "80-84세", "85세이상"]}
# MoHW by sido 2022-2024 (cross-check)
msido = collections.defaultdict(dict)
for r in list(csv.reader(open("u1.csv")))[1:]:
    msido[r[1].split()[0]][int(r[0])] = sum(int(x) for x in r[2:])

out = {"years": YEARS, "units": units, "sido": sido, "nat": {"h": nat_h, "p": nat_p}, "mohw": mohw, "mohwSido": msido, "W": G["W"], "H": G["H"], "sidoPaths": G["sido"]}
json.dump(out, open(f"{S}/q4_data.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("nat", nat_h, [round(h / p * 100, 1) for h, p in zip(nat_h, nat_p)])
for s in sido:
    print(SHORT[s], sido[s]["h"][-1], round(sido[s]["h"][-1] / sido[s]["p"][-1] * 100, 1), round(sido[s]["h"][0] / sido[s]["p"][0] * 100, 1))
r = sorted(units, key=lambda u: -u["h"][-1] / max(1, u["p"][-1]))
print("top rate", [(u["sido"], u["name"], round(u["h"][-1] / u["p"][-1] * 100, 1), u["h"][-1]) for u in r[:8]])
print("low rate", [(u["sido"], u["name"], round(u["h"][-1] / u["p"][-1] * 100, 1), u["h"][-1]) for u in r[-6:]])
r = sorted(units, key=lambda u: -u["h"][-1])
print("top count", [(u["sido"], u["name"], u["h"][-1], round(u["h"][-1] / u["p"][-1] * 100, 1)) for u in r[:8]])
print("mohw", {a: (v[0], v[-1]) for a, v in mohw.items()})
