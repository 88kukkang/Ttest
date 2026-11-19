import csv,io,subprocess,re,collections,json,sys
D='/tmp/claude-0/-home-user/867911d4-434e-5c1c-a4fa-95438af19a83/scratchpad/q2/'
YRS=[2011,2014,2015,2016,2017,2019,2021,2022,2023,2024]
def rows(y):
    t=subprocess.run(['iconv','-f','cp949','-t','utf-8',D+f'y_{y}.bin'],capture_output=True).stdout.decode()
    return list(csv.reader(io.StringIO(t)))
def num(s):
    s=s.strip().replace(',','')
    return int(float(s)) if s not in ('','-') else 0
def parse(y):
    R=rows(y); h=[c.strip() for c in R[0]]
    cols={}
    for i,c in enumerate(h):
        m=re.search(r'(?<![A-Za-z])([ABCDEFGHT])-?(\d{1,2})(?![0-9A-Z])',c)
        if m and '0-0' not in c: cols[i]=m.group(1)+m.group(2)
        elif c.startswith('기타') and 'G' not in c: cols[i]='ETC'
    ni=next(i for i,c in enumerate(h) if c.replace(' ','') in ('국적','국적명','국적별'))
    out=collections.defaultdict(lambda:collections.Counter()); skipped=[]
    for r in R[1:]:
        if len(r)<len(h)-2: continue
        name=re.sub(r'\s+','',r[ni])
        if not name or re.search(r'(주계|총계|합계)$',name) or name in('총계','합계','계'): skipped.append(name); continue
        for i,code in cols.items():
            if i<len(r): out[name][code]+=num(r[i])
    return out,cols,skipped
if __name__=='__main__':
    for y in YRS:
        o,c,sk=parse(y); tot=sum(sum(v.values()) for v in o.values())
        print(y,len(o),'total',tot,'codes',len(set(c.values())),'skipped',sorted(set(sk))[:8])
