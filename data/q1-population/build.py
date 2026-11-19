import csv,io,subprocess,re,collections,json,sys
D='/tmp/claude-0/-home-user/867911d4-434e-5c1c-a4fa-95438af19a83/scratchpad/q1/'
SIDO={'강원도':'강원특별자치도','전라북도':'전북특별자치도','광주광역시':'전남광주통합특별시','전라남도':'전남광주통합특별시'}
SGG={('경상북도','군위군'):('대구광역시','군위군'),('인천광역시','남구'):('인천광역시','미추홀구')}
def load(ym):
    t=subprocess.run(['iconv','-f','cp949','-t','utf-8',D+f'pd_{ym}.csv'],capture_output=True).stdout.decode()
    r=list(csv.reader(io.StringIO(t)));dong=[]
    for row in r[1:]:
        m=re.match(r'(.*?)\s*\((\d{10})\)$',row[0]); name,code=m.group(1),m.group(2)
        if code[5:]=='00000': continue
        parts=re.sub(r'\s+',' ',name).strip().split(' ')
        sido=SIDO.get(parts[0],parts[0]); rest=parts[1:-1]; dn=parts[-1]
        city=rest[0] if rest else ''
        k=SGG.get((parts[0],city)) or SGG.get((sido,city))
        if k: sido,city=k
        if sido=='인천광역시' and city in ('중구','동구','서구','제물포구','영종구','서해구','검단구'): city='중구·동구·서구'
        gu=rest[1] if len(rest)>1 else ''
        if city=='창원시' and dn=='중앙동': dn=gu+' '+dn
        ages=[int(x.replace(',','')) for x in row[3:]]
        dong.append(dict(gu=gu,code=code,sido=sido,city=city,dong=dn,pop=int(row[1].replace(',','')),ages=ages,full=' '.join(parts)))
    return dong
a=load('201610');b=load('202610')
key=lambda x:(x['sido'],x['city'],x['dong'])
A={};B={}
for x in a: A.setdefault(key(x),[]).append(x)
for x in b: B.setdefault(key(x),[]).append(x)
dup=[k for k in A if len(A[k])>1]+[k for k in B if len(B[k])>1]; print('dups',dup[:5])
both=set(A)&set(B)
print('matched',len(both),'of',len(B),'pop share', sum(B[k][0]['pop'] for k in both)/sum(x['pop'] for x in b))
cities=sorted({(x['sido'],x['city']) for x in b}); ca={(x['sido'],x['city']) for x in a}
print('cities',len(cities),'missing in 2016',[c for c in cities if c not in ca], [c for c in ca if c not in set(cities)])
um=collections.Counter((k[0],k[1]) for k in B if k not in both); print('cities with unmatched',len(um), um.most_common(12))

units=[]
for k in sorted(both):
    x,y=A[k][0],B[k][0]
    units.append(dict(code=y['code'],sido=k[0],city=k[1],dong=k[2],p0=x['pop'],p1=y['pop'],a0=x['ages'],a1=y['ages'],comp=False))
ua=collections.defaultdict(lambda:[0,[0]*11,0]);ub=collections.defaultdict(lambda:[0,[0]*11,0])
for k,v in A.items():
    if k not in both: c=ua[(k[0],k[1])]; c[0]+=v[0]['pop']; c[1]=[p+q for p,q in zip(c[1],v[0]['ages'])]; c[2]+=1
for k,v in B.items():
    if k not in both: c=ub[(k[0],k[1])]; c[0]+=v[0]['pop']; c[1]=[p+q for p,q in zip(c[1],v[0]['ages'])]; c[2]+=1
for c in set(ua)|set(ub):
    units.append(dict(code=min([v[0]['code'] for k,v in B.items() if (k[0],k[1])==c and k not in both] or ['9']),sido=c[0],city=c[1],dong=f"경계가 바뀐 동 묶음({ub[c][2]}곳)",p0=ua[c][0],p1=ub[c][0],a0=ua[c][1],a1=ub[c][1],comp=True))
T0=sum(x['pop'] for x in a);T1=sum(x['pop'] for x in b);print('national',T0,T1,T1-T0,(T1/T0-1)*100)
city=collections.defaultdict(lambda:[0,0])
for u in units: c=city[(u['sido'],u['city'])]; c[0]+=u['p0']; c[1]+=u['p1']
shr={c for c,v in city.items() if v[1]<v[0]}
print('cities',len(city),'shrank',len(shr),'grew',len(city)-len(shr))
M=[u for u in units if not u['comp'] and u['p0']>0]
g=[u for u in M if u['p1']>u['p0']]; print('matched dongs',len(M),'grew',len(g), 'pop in grew 2026', sum(u['p1'] for u in g)/T1)
gi=[u for u in g if (u['sido'],u['city']) in shr]; print('grew inside shrinking cities',len(gi), 'of dongs in shrinking', sum(1 for u in M if (u['sido'],u['city']) in shr))
print('cities shrinking with >=1 growing dong', len({(u['sido'],u['city']) for u in gi}))
gi.sort(key=lambda u:u['p0']-u['p1'])
for u in gi[:15]: print(u['sido'],u['city'],u['dong'],u['p0'],u['p1'],round((u['p1']/u['p0']-1)*100,1), 'city', city[(u['sido'],u['city'])])
# age: share 0-9 among grew vs shrank (2026)
for nm,S in (('grew',g),('shrank',[u for u in M if u['p1']<u['p0']])):
    tot=sum(u['p1'] for u in S); kid=sum(u['a1'][0] for u in S); old=sum(sum(u['a1'][7:]) for u in S)
    print(nm, 'kids0-9',round(kid/tot*100,1),'70+',round(old/tot*100,1))
by=collections.defaultdict(lambda:[0,0,0,0])
for u in M:
    s=by[u['sido']]; s[0]+=1; s[1]+= u['p1']>u['p0']
for c,v in city.items(): s=by[c[0]]; s[2]+=1; s[3]+= v[1]<v[0]
for k,v in by.items(): print(k,v)
json.dump(dict(units=units,city={f'{k[0]}|{k[1]}':v for k,v in city.items()},T=[T0,T1]),open('q1_raw.json','w'),ensure_ascii=False)

YS=list(range(2016,2027))
Y={y:{} for y in YS}
for y in YS:
    for x in load(f'{y}10'): Y[y].setdefault(key(x),0); Y[y][key(x)]+=x['pop']
miss=collections.Counter()
ser={}
for k in both:
    ser[k]=[Y[y].get(k) for y in YS]
    for i,v in enumerate(ser[k]):
        if v is None: miss[YS[i]]+=1
print('matched missing by year',dict(miss))
cs=collections.defaultdict(lambda:[0]*len(YS))
for i,y in enumerate(YS):
    for k,v in Y[y].items():
        if k not in both: cs[(k[0],k[1])][i]+=v
mk=[k for k in both if None in ser[k]]
print(mk[:10])

badcy={(k[0],k[1],i) for k in mk for i,y in enumerate(YS) if Y[y].get(k) is None}
OUT=[]
for u in sorted(units,key=lambda u:u['code']):
    c=(u['sido'],u['city'])
    if u['comp']: s=list(cs[c])
    else: s=list(ser[(u['sido'],u['city'],u['dong'])])
    s=[None if (c[0],c[1],i) in badcy else v for i,v in enumerate(s)]
    OUT.append([u['sido'],u['city'],u['dong'],1 if u['comp'] else 0,s])
# age shares 2016/2026 for matched grew vs shrank
AG={}
for nm,S in (('grew',g),('shrank',[u for u in M if u['p1']<u['p0']])):
    for yy,f in (('2016','a0'),('2026','a1')):
        tot=[sum(u[f][i] for u in S) for i in range(11)]; T=sum(tot); AG[nm+yy]=[round(v/T*100,2) for v in tot]
    AG[nm+'n']=len(S)
# monthly change file Oct 2026
t=subprocess.run(['iconv','-f','cp949','-t','utf-8',D+'f.bin'],capture_output=True).stdout.decode()
R=list(csv.DictReader(io.StringIO(t)))
mon=collections.Counter('up' if int(r['전체 인구증감'])>0 else 'down' if int(r['전체 인구증감'])<0 else 'zero' for r in R if r['읍면동명'])
print('month',mon, len(R))
json.dump(dict(Y=YS,U=OUT,AG=AG,T=[T0,T1],mon=dict(mon)),open('../q1_data.json','w'),ensure_ascii=False,separators=(',',':'))
print(AG)
