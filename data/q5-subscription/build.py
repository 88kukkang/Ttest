import csv,io,subprocess,collections,json,statistics
D='/tmp/claude-0/-home-user/867911d4-434e-5c1c-a4fa-95438af19a83/scratchpad/q5/'
rd=lambda f: list(csv.DictReader(io.StringIO(subprocess.run(['iconv','-f','cp949','-t','utf-8',D+f],capture_output=True).stdout.decode())))
G=rd('g.bin'); B=rd('b.bin')
info={r['주택관리번호']:r for r in B}
print('cols B',list(B[0].keys())[:20])
print('B types',collections.Counter(r['주택구분코드명'] for r in B), collections.Counter(r['분양구분코드명'] for r in B))
print('B dates',min(r['모집공고일'] for r in B),max(r['모집공고일'] for r in B))
cx=collections.defaultdict(lambda:{'sup':{},'r1':0,'r2':0,'r1loc':0})
for r in G:
    c=cx[r['주택관리번호']]; m=(r['모델번호'],r['주택형'])
    c['sup'][m]=int(r['공급세대수'] or 0)
    n=int(r['접수건수'] or 0)
    if r['순위']=='1': c['r1']+=n
    else: c['r2']+=n
print('complexes',len(cx),'with info',sum(1 for k in cx if k in info))
print(collections.Counter(r['거주지역'] for r in G), collections.Counter(r['순위'] for r in G))
U=[]
for k,c in cx.items():
    if k not in info: continue
    i=info[k]; sup=sum(c['sup'].values())
    if sup<=0: continue
    loc=i['공급위치'].split(); city=loc[1] if len(loc)>1 else ''
    U.append(dict(id=k,name=i['주택명'],sido=i['공급지역명'],city=city,date=i['모집공고일'],sup=sup,r1=c['r1'],ratio=c['r1']/sup,kind=i['주택구분코드명'],pub=i['분양구분코드명'],addr=i['공급위치']))
print(len(U), collections.Counter(u['sido'] for u in U))
big=[u for u in U if u['sup']>=50]
top=sorted(big,key=lambda u:-u['ratio'])[:50]
print('top50 by sido',collections.Counter(u['sido'] for u in top))
for u in top[:25]: print(u['date'],u['sido'],u['city'],u['name'][:30],u['sup'],u['r1'],round(u['ratio'],1))
# per year top 20
for y in range(2020,2026):
    yy=[u for u in big if u['date'][:4]==str(y)]; t=sorted(yy,key=lambda u:-u['ratio'])[:20]
    print(y,len(yy),'top20',collections.Counter(u['sido'] for u in t).most_common(6))
# sido totals
S=collections.defaultdict(lambda:[0,0,0,[]])
for u in U: s=S[u['sido']]; s[0]+=u['sup']; s[1]+=u['r1']; s[2]+=1; s[3].append(u['ratio'])
for k,v in sorted(S.items(),key=lambda x:-x[1][1]/x[1][0]): print(k,v[2],v[0],v[1],round(v[1]/v[0],1),'median',round(statistics.median(v[3]),2))
json.dump(U,open('units.json','w'),ensure_ascii=False)
