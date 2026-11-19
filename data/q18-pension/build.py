import csv,glob,io,subprocess,json,collections
D='/tmp/claude-0/-home-user/867911d4-434e-5c1c-a4fa-95438af19a83/scratchpad/q18/'
rows=[]
for f in glob.glob(D+'zz/*.csv'):
    t=subprocess.run(['iconv','-f','cp949','-t','utf-8',f],capture_output=True).stdout.decode(); rows+=list(csv.DictReader(io.StringIO(t)))
q4=json.load(open('/home/user/Test/data/q4-elderly/q4_data.json'))
SH={'서울특별시':'서울','부산광역시':'부산','대구광역시':'대구','인천광역시':'인천','광주광역시':'광주','대전광역시':'대전','울산광역시':'울산','세종특별자치시':'세종','경기도':'경기','강원도':'강원','강원특별자치도':'강원','충청북도':'충북','충청남도':'충남','전라북도':'전북','전북특별자치도':'전북','전라남도':'전남','경상북도':'경북','경상남도':'경남','제주특별자치도':'제주'}
GJ={'동구','서구','남구','북구','광산구'}
def key(r):
    s=r['통계시도명']; n=r['통계시군구명']
    sd=SH.get(s) or (('광주' if n in GJ else '전남') if s=='전남광주통합특별시' else None)
    if sd=='세종': n='세종시'
    if sd=='인천' and n in ('중구','동구','서구','제물포구','영종구','서해구','검단구'): n='INC'
    if sd=='경북' and n=='군위군': sd='대구'
    if sd=='인천' and n=='남구': n='미추홀구'
    return sd,n.replace(' ','')
by=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0]))
for r in rows:
    k=key(r); a=by[r['통계연월']][k]; a[0]+=int(r['수급자수']); a[1]+=int(r['65세이상인구수'])
YM=sorted(by)
def unit_key(u):
    sd,n=u['sido'],u['name']
    if sd=='인천' and n in ('중구','동구','서구'): return [(sd,'INC')]
    return [(sd,n)]
def lookup(ym,u):
    m=by[ym]; sd,n=u['sido'],u['name']
    if sd=='인천' and n in('중구','동구','서구'): k=(sd,'INC')
    else: k=(sd,n)
    if k in m: return m[k]
    if sd=='대구' and n=='군위군' and ('경북','군위군') in m: return m[('경북','군위군')]
    for (s2,n2),v in m.items():   # city-level row covering 일반구 polygons
        if s2==sd and n.startswith(n2) and n2.endswith('시'): return v
    return None
U=[]; miss=collections.Counter()
for u in q4['units']:
    ser=[]
    for ym in YM:
        v=lookup(ym,u); ser.append(None if v is None or not v[1] or not sum(x[1] for x in by[ym].values()) else round(v[0]/v[1]*100,2))
        if v is None: miss[ym]+=1
    h=u['h'][-1]/u['p'][-1]*100 if u['p'][-1] else None
    U.append([u['code'],u['sido'],u['name'],u['d'],u['c'],ser,round(h,1) if h else None])
print('missing by ym',dict(list(miss.items())[:5]),sum(miss.values()))
nat=[]
for ym in YM:
    s=sum(v[0] for v in by[ym].values()); p=sum(v[1] for v in by[ym].values()); nat.append(round(s/p*100,2) if p else None)
last={k:v for k,v in by['202609'].items()}
tot=sum(v[0] for v in last.values()), sum(v[1] for v in last.values())
print('nat 2026-09',tot, nat[-1], 'nat 2015-09',nat[0])
srt=sorted(((v[0]/v[1]*100,k,v) for k,v in last.items() if v[1]),reverse=True)
print('top',[(round(a,1),k) for a,k,_ in srt[:8]]); print('bottom',[(round(a,1),k) for a,k,_ in srt[-8:]])
json.dump({'ym':YM,'nat':nat,'U':U,'W':q4['W'],'H':q4['H'],'sidoPaths':q4.get('sidoPaths')},open('/tmp/claude-0/-home-user/867911d4-434e-5c1c-a4fa-95438af19a83/scratchpad/q18_data.json','w'),ensure_ascii=False,separators=(',',':'))
# group by type
typ=collections.defaultdict(lambda:[0,0])
for (sd,n),v in last.items():
    t='광역시 구' if n.endswith('구') and sd in('서울','부산','대구','인천','광주','대전','울산') or n=='INC' else ('군' if n.endswith('군') else '시')
    typ[t][0]+=v[0]; typ[t][1]+=v[1]
print({k:round(v[0]/v[1]*100,1) for k,v in typ.items()})
