import json,collections,re
r=json.load(open('q19_raw.json')); q4=json.load(open('/home/user/Test/data/q4-elderly/q4_data.json'))
k8=r['k08']; k26=r['k26']; S=r['S']
ALIAS08={('충남','당진시'):[('충남','당진군')],('경기','여주시'):[('경기','여주군')],('대구','군위군'):[('경북','군위군')],('세종','세종시'):[('충남','연기군')],
 ('인천','미추홀구'):[('인천','남구')]}
def city(n):
    m=re.match(r'^(.+?시)(.+구)$',n); return m.group(1) if m else n
def val(d,sd,n,year):
    if f'{sd}|{n}' in d: return d[f'{sd}|{n}']
    if year=='08' and (sd,n) in ALIAS08: return sum(d.get(f'{a}|{b}',0) for a,b in ALIAS08[(sd,n)])
    return None
places={}
for u in q4['units']:
    sd,n=u['sido'],u['name']; c=city(n) if sd not in('서울','부산','대구','인천','광주','대전','울산') else n
    key=(sd,c); p=places.setdefault(key,{'units':[],'cx':[],'cy':[]}); p['units'].append(u['code']); p['cx'].append(u['c'][0]); p['cy'].append(u['c'][1])
def place_children(sd,c,units_names,yy):
    d=k8 if yy=='08' else k26
    v=val(d,sd,c,yy)
    if v is not None: return v
    # city with 일반구 in data: sum all entries starting with city
    s=[x for k,x in d.items() if k.startswith(f'{sd}|{c}')]
    if s: return sum(s)
    if yy=='08' and sd=='경남' and c=='창원시': return sum(d.get(f'경남|{x}',0) for x in ('창원시','마산시','진해시'))
    return None
miss=[]
for (sd,c),p in places.items():
    a=place_children(sd,c,None,'08'); b=place_children(sd,c,None,'26')
    if sd=='경남' and c=='창원시': a=sum(v for k,v in k8.items() if k.startswith('경남|창원시') or k.startswith('경남|마산시') or k.startswith('경남|진해시'))
    p['k08']=a; p['k26']=b
    if a is None or b is None: miss.append((sd,c,a,b))
print('miss',miss)
# closures -> place
def place_of(sd,n):
    n=n.replace(' ','')
    if (sd,n) in places: return (sd,n)
    c=city(n)
    if (sd,c) in places: return (sd,c)
    for (s2,c2) in places:
        if s2==sd and (c2.endswith(n) or n.startswith(c2)): return (s2,c2)
    if sd=='경남' and n.endswith('구'): return ('경남','창원시')
    if sd=='인천' and n=='영종구': return ('인천','중구')
    if sd=='대구' and n=='군위군': return ('대구','군위군')
    return None
cnt=collections.Counter(); bad=collections.Counter()
for x in S:
    k=place_of(x[0],x[1])
    if k is None: bad[(x[0],x[1])]+=1; continue
    places[k].setdefault('cl',[]).append(x[3])
print('unplaced',bad)
P=[]
for (sd,c),p in places.items():
    P.append([sd,c,round(sum(p['cx'])/len(p['cx']),1),round(sum(p['cy'])/len(p['cy']),1),p['k08'],p['k26'],sorted(p.get('cl',[])),p['units']])
json.dump({'P':P,'U':[[u['code'],u['d']] for u in q4['units']],'W':q4['W'],'H':q4['H'],'sidoPaths':q4['sidoPaths']},open('q19_map.json','w'),ensure_ascii=False,separators=(',',':'))
dec=[(p[5]/p[4]-1)*100 for p in P if p[4] and p[5]]
print(len(P), 'places with >40% child loss', sum(1 for x in dec if x<-40), 'of', len(dec))
z=[p for p in P if p[4] and p[5] and (p[5]/p[4]-1)*100<-40 and not [y for y in p[6] if y>=2009]]; print('>40% loss & no closure since 2009',len(z), [(p[0],p[1]) for p in z][:12])
