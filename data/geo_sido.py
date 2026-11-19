"""시도 지도 도형과 중심점(시군구 중심의 평균). ../q19-closures/q19_data.json 의 도형을 다시 쓴다."""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
SH = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
      "강원특별자치도": "강원", "강원도": "강원", "충청북도": "충북", "충청남도": "충남", "전라북도": "전북", "전북특별자치도": "전북", "전라남도": "전남", "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주"}
def geo():
    G = json.load(open(os.path.join(H, "q19-closures", "q19_data.json"), encoding="utf-8")); cen = {}
    for p in G["P"]: cen.setdefault(p[0], []).append((p[2], p[3]))
    cen = {s: [round(sum(x for x, _ in v) / len(v), 1), round(sum(y for _, y in v) / len(v), 1)] for s, v in cen.items()}
    cw = next(p for p in G["P"] if p[1] == "창원시"); cen["창원"] = [cw[2], cw[3]]
    xs = [p[2] for p in G["P"]]; ys = [p[3] for p in G["P"]]
    return {"paths": [{"n": SH.get(sp["name"], sp["name"]), "d": sp["d"]} for sp in G["sidoPaths"]], "cen": cen, "box": [min(xs) - 24, min(ys) - 24, max(xs) + 24, max(ys) + 24]}
if __name__ == "__main__":
    g = geo(); print([p["n"] for p in g["paths"]], g["cen"], g["box"])
