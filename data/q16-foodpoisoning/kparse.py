import json,re,html,sys
def parse(fn):
    j=json.loads(open(fn).read()); h=j['result'][0]
    rows=re.findall(r'<tr[^>]*>(.*?)</tr>',h,re.S); out=[]
    for r in rows:
        cells=[]
        for m in re.finditer(r'<t([hd])([^>]*)>(.*?)</t[hd]>',r,re.S):
            cs=re.search(r'colspan=["\']?(\d+)',m.group(2)); cells.append((html.unescape(re.sub(r'<[^>]+>','',m.group(3))).strip(), int(cs.group(1)) if cs else 1))
        out.append(cells)
    return out
def num(s):
    s=s.replace(',','').strip()
    try: return float(s)
    except: return None
def table(fn, label='합계'):
    R=parse(fn)
    # header rows until first data row; expand colspans
    hdr=[]; data={}
    for r in R:
        if r and r[0][0] and num(r[1][0]) is not None if len(r)>1 else False:
            data[r[0][0]]=[num(c[0]) for c in r[1:]]
        elif r and any(c[0] for c in r):
            row=[]; [row.extend([c[0]]*c[1]) for c in r]; hdr.append(row)
    return hdr,data
if __name__=='__main__':
    h,d=table(sys.argv[1]); [print(x[:40]) for x in h]; print(list(d.items())[:2])
