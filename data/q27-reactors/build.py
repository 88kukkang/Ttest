import csv,io,subprocess,json,collections,datetime,statistics
D='/tmp/claude-0/-home-user/867911d4-434e-5c1c-a4fa-95438af19a83/scratchpad/q27/'
cp=lambda f: list(csv.reader(io.StringIO(subprocess.run(['iconv','-f','cp949','-t','utf-8',D+f],capture_output=True).stdout.decode())))
u8=lambda f: list(csv.reader(open(D+f,encoding='utf-8-sig')))
G=u8('f.bin'); OH=cp('15114951.bin'); PL=cp('15060801.bin'); UT=u8('15046075.bin'); AC=cp('15074543.bin')
UNITS=['고리1호기','고리2호기','고리3호기','고리4호기','신고리1호기','신고리2호기','새울1호기','새울2호기','월성1호기','월성2호기','월성3호기','월성4호기','신월성1호기','신월성2호기','한빛1호기','한빛2호기','한빛3호기','한빛4호기','한빛5호기','한빛6호기','한울1호기','한울2호기','한울3호기','한울4호기','한울5호기','한울6호기','신한울1호기','신한울2호기']
# 원안위 header order matches UNITS order (고리1-4, 고리1·2두중=신고리1·2, 새울1·2, 월성1-4, 월성S1·2=신월성1·2, 한빛1-6, 한울1-6, 신한울1·2)
hdr=UT[0][1:]; assert len(hdr)==28
util={}
for r in UT[1:]:
    y=int(r[0])
    for i,v in enumerate(r[1:29]):
        if v.strip(): util.setdefault(UNITS[i],{})[y]=float(v)
gen={}
for r in G[1:]: gen.setdefault(r[0],{})[int(r[1])]=[float(r[2]),float(r[3])]
ohs={}
for r in OH[1:]:
    if len(r)<6 or not r[3]: continue
    ohs.setdefault(r[1],set()).add((r[3],r[4],r[2]))
for r in PL[1:]:
    if len(r)<5 or not r[2]: continue
    ohs.setdefault(r[0],set()).add((r[2],r[3],r[1]))
OHL={}
for u,v in ohs.items():
    best={}
    for s,e,n in v:
        e=e or '2026-12-31'
        if s not in best or e>best[s][0]: best[s]=(e,n)
    OHL[u]=sorted((s,e,n) for s,(e,n) in best.items())
miss=[u for u in OHL if u not in UNITS]; print('oh units not in list',miss)
acc={}
for r in AC[1:]:
    if r[1] in ('수동','자동'): acc.setdefault(r[0],0); acc[r[0]]+=sum(int(x or 0) for x in r[2:])
# national mean utilization by year
nat={y:round(statistics.mean([util[u][y] for u in UNITS if y in util.get(u,{})]),1) for y in range(1978,2026)}
ncount={y:sum(1 for u in UNITS if y in util.get(u,{})) for y in range(1978,2026)}
print({y:(nat[y],ncount[y]) for y in (1990,2000,2008,2012,2013,2017,2018,2019,2022,2025)})
tg={y:round(sum(gen[u][y][0] for u in gen if y in gen[u])/1e6,1) for y in range(2014,2026)}; print('TWh',tg)
lens=[]
for u,l in OHL.items():
    for s,e,n in l:
        d=(datetime.date.fromisoformat(e)-datetime.date.fromisoformat(s)).days; lens.append((d,u,s,e,n))
lens.sort(); print(len(lens),'median',statistics.median([x[0] for x in lens]), lens[-8:])
print('acc',acc)
json.dump({'U':UNITS,'util':util,'gen':gen,'oh':OHL,'acc':acc,'nat':nat,'ncount':ncount},open(D+'../q27_data.json','w'),ensure_ascii=False,separators=(',',':'))
