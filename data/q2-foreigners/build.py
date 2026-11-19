import sys; sys.path.insert(0,'.')
from parse import *
G={'work':['E1','E2','E3','E4','E5','E6','E7','E8','E9','E10','D3','D7','D8','D9'],
   'kin':['F4','H2'],'perm':['F5'],'marr':['F6'],'study':['D2','D4'],'fam':['F1','F2','F3'],
   'etc':['A1','A2','A3','D1','D5','D6','D10','G1','H1','ETC'],
   'short':['B1','B2','C1','C2','C3','C4','T1']}
code2g={c:g for g,cs in G.items() for c in cs}
NORM={'태국':'타이','(타이완)':'타이완'}
data={}
for y in YRS:
    o,c,_=parse(y); d=collections.defaultdict(lambda:collections.Counter())
    unk=collections.Counter()
    for n,v in o.items():
        n=NORM.get(n,n)
        for code,x in v.items():
            g=code2g.get(code)
            if g is None: unk[code]+=x; continue
            d[n][g]+=x
    if unk: print(y,'unknown',unk)
    data[y]=d
ORDER=['work','kin','study','perm','fam','marr','etc']
def lt(c): return sum(c[g] for g in ORDER)
top=sorted(data[2024],key=lambda n:-lt(data[2024][n]))[:12]
print(top)
out={'years':YRS,'groups':ORDER+['short'],'nat':top+['그 밖의 나라'],'v':{}}
for y in YRS:
    rows=[]
    for n in top: rows.append([data[y][n][g] for g in out['groups']])
    other=[sum(data[y][n][g] for n in data[y] if n not in top) for g in out['groups']]
    rows.append(other); out['v'][y]=rows
    T=[sum(r[i] for r in rows) for i in range(len(out['groups']))]; L=sum(T[:7])
    print(y,'long',L,'short',T[7],' '.join(f"{g}:{T[i]/L*100:.1f}" for i,g in enumerate(ORDER)))
# 2024 detail codes for notes
o,_,_=parse(2024); tot=collections.Counter()
for v in o.values(): tot.update(v)
out['codes2024']=dict(tot)
json.dump(out,open('../q2_data.json','w'),ensure_ascii=False,separators=(',',':'))
for n in top: c=data[2024][n]; L=lt(c); print(n,L,{g:round(c[g]/L*100) for g in ORDER})
