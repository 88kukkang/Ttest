import csv,io,subprocess,collections,json,datetime,re
D='/tmp/claude-0/-home-user/867911d4-434e-5c1c-a4fa-95438af19a83/scratchpad/q23/'
def load(f):
    t=subprocess.run(['iconv','-f','cp949','-t','utf-8',D+f],capture_output=True).stdout.decode()
    return list(csv.DictReader(io.StringIO(t)))
CAUSE=['부주의','전기적 요인','기계적 요인','방화','자연적인 요인','기타','미상']
def cause(r):
    c=r['발화요인대분류'].strip()
    if c in ('방화','방화의심'): return '방화'
    if c in CAUSE: return c
    if c in ('화학적 요인','교통사고','제품결함','가스누출(폭발)'): return '기타'
    return '미상' if not c else '기타'
HEAT={'굴뚝(연통) 아궁이','모닥불, 연탄, 숯'}
Y=list(range(2015,2025))
mon=collections.defaultdict(lambda:[[0]*len(CAUSE) for _ in range(12)])
dth=collections.defaultdict(lambda:[0]*12); heat=collections.defaultdict(lambda:[0]*12)
hour=[[0]*len(CAUSE) for _ in range(24)]
sub=collections.Counter(); subm=collections.defaultdict(lambda:[0]*12)
place_m=collections.defaultdict(lambda:[0]*12)
grid=[[0]*24 for _ in range(366)]; gridc=[[collections.Counter() for _ in range(24)] for _ in range(366)]
for y in Y:
    R=load('f.bin' if y==2024 else f'y_{y}.bin')
    for r in R:
        ts=r.get('일시') or r.get('화재발생년월일') or ''
        m=re.match(r'(\d{4})-(\d{2})-(\d{2})(?:\s+(\d{1,2}):(\d{2}))?',ts)
        if not m: continue
        mo=int(m.group(2))-1; hr=int(m.group(4)) if m.group(4) else None
        c=cause(r); ci=CAUSE.index(c)
        mon[y][mo][ci]+=1
        try: dth[y][mo]+=int(r['사망'] or 0)
        except: pass
        hs=r.get('발화열원소분류','')
        if hs in HEAT: heat[y][mo]+=1
        sc=r['발화요인소분류'].strip(); sub[sc]+=1; subm[sc][mo]+=1
        pl=r['장소대분류'].strip(); place_m[pl][mo]+=1
        if hr is not None: hour[hr][ci]+=1
        if y==2024 and hr is not None:
            doy=datetime.date(int(m.group(1)),mo+1,int(m.group(3))).timetuple().tm_yday-1
            grid[doy][hr]+=1; gridc[doy][hr][ci]+=1
    print(y,len(R),sum(sum(x) for x in mon[y]))
tot=[sum(sum(mon[y][m]) for y in Y) for m in range(12)]; T=sum(tot)
print('month share',[round(x/T*100,1) for x in tot])
print('cause share',[ (CAUSE[i],round(sum(mon[y][m][i] for y in Y for m in range(12))/T*100,1)) for i in range(len(CAUSE))])
dt=[sum(dth[y][m] for y in Y) for m in range(12)]; print('deaths by month',dt, sum(dt))
ht=[sum(heat[y][m] for y in Y) for m in range(12)]; print('heat-source fires',ht,sum(ht),round(sum(ht)/T*100,1))
print('hour has', sum(sum(h) for h in hour))
top=[k for k,_ in sub.most_common(14)]
json.dump({'Y':Y,'CAUSE':CAUSE,'mon':{y:mon[y] for y in Y},'dth':{y:dth[y] for y in Y},'heat':{y:heat[y] for y in Y},'hour':hour,
  'sub':{k:subm[k] for k in top},'place':{k:v for k,v in place_m.items()},'grid':grid,'gridDom':[[ (max(gridc[d][h],key=gridc[d][h].get) if gridc[d][h] else None) for h in range(24)] for d in range(366)]},
  open(D+'../q23_raw.json','w'),ensure_ascii=False)
for k in top: v=subm[k]; s=sum(v); print(k,s,[round(x/s*100) for x in v])
