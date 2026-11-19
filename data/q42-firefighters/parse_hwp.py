"""소방청 「연도별 소방공무원 순직 및 공상자 현황」(공공데이터포털 15131241, hwp 두 개가 든 zip)에서 표를 꺼낸다.
hwp 5 문서는 OLE 묶음이고 BodyText/Section* 이 (압축된) 레코드 열이다. 표의 칸은 LIST_HEADER(72)로 시작하고
글자는 PARA_TEXT(67)에 UTF-16으로 들어 있다. 빈칸도 칸으로 세어야 열이 밀리지 않는다.  (pip install olefile)"""
import io, os, struct, sys, zipfile, zlib, json
import olefile
H = os.path.dirname(os.path.abspath(__file__))
def cells(data):
    out = []; i = 0; cur = None
    while i + 4 <= len(data):
        h = struct.unpack("<I", data[i:i + 4])[0]; tag = h & 0x3ff; size = h >> 20; i += 4
        if size == 0xfff: size = struct.unpack("<I", data[i:i + 4])[0]; i += 4
        body = data[i:i + size]; i += size
        if tag == 72: cur = []; out.append(cur)          # 새 칸
        elif tag == 67:
            s = ""; j = 0
            while j + 2 <= len(body):
                c = struct.unpack("<H", body[j:j + 2])[0]
                if c < 32: j += 16 if c in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23) else 2; continue
                s += chr(c); j += 2
            if cur is None: cur = []; out.append(cur)
            cur.append(s.strip())
    return ["".join(c).replace(" ", "") for c in out]
def docs():
    z = zipfile.ZipFile(os.path.join(H, "raw", "firefighter_casualties.zip")); res = {}
    for i in z.infolist():
        if not i.filename.lower().endswith(".hwp"): continue
        try: nm = i.filename.encode("cp437").decode("cp949")
        except Exception: nm = i.filename
        o = olefile.OleFileIO(io.BytesIO(z.read(i))); comp = o.openstream("FileHeader").read()[36] & 1; cs = []
        for st in sorted(o.listdir()):
            if st[0] == "BodyText":
                d = o.openstream(st).read(); cs += cells(zlib.decompress(d, -15) if comp else d)
        res[os.path.basename(nm)] = cs
    return res
if __name__ == "__main__":
    for nm, cs in docs().items(): print("##", nm, len(cs)); print("|".join(cs)[:1800])
