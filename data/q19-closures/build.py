import pandas as pd, csv, io, subprocess, re, collections, json
D='/tmp/claude-0/-home-user/867911d4-434e-5c1c-a4fa-95438af19a83/scratchpad/q19/'
df=pd.read_excel(D+'std.xls',header=1,dtype=str)
df=df[df['시도교육청명']!='전라남도교육청']
df['폐교연도']=df['폐교연도'].astype(int)
print(len(df))
SH={'서울특별시':'서울','부산광역시':'부산','대구광역시':'대구','인천광역시':'인천','광주광역시':'광주','대전광역시':'대전','울산광역시':'울산','세종특별자치시':'세종','경기도':'경기','강원도':'강원','강원특별자치도':'강원','충청북도':'충북','충청남도':'충남','전라북도':'전북','전북특별자치도':'전북','전라남도':'전남','경상북도':'경북','경상남도':'경남','제주특별자치도':'제주'}
GJ={'동구','서구','남구','북구','광산구'}
def sd(s,n): return SH.get(s) or (('광주' if n in GJ else '전남') if s=='전남광주통합특별시' else s)
S=[]
for _,r in df.iterrows():
    S.append([sd(r['시도명'],r['시군구명']), r['시군구명'], r['폐교명'], int(r['폐교연도']), {'초등학교':'e','중학교':'m','고등학교':'h'}[r['학교급구분명']], {'대부':'l','미활용':'u','자체활용':'s'}[r['활용현황구분명']]])
yc=collections.Counter(x[3] for x in S); print(sorted(yc.items()))
print(collections.Counter(x[0] for x in S).most_common())
print(collections.Counter(x[5] for x in S))
# children 0-9 by sigungu
def sg(ym):
    t=subprocess.run(['iconv','-f','cp949','-t','utf-8',D+f'sg_{ym}.csv'],capture_output=True).stdout.decode()
    r=list(csv.reader(io.StringIO(t))); out={}
    for row in r[1:]:
        m=re.match(r'(.*?)\s*\((\d{10})\)$',row[0]); nm=re.sub(r'\s+',' ',m.group(1)).strip().split(' ')
        if len(nm)<2: continue
        s=nm[0]; n=''.join(nm[1:])
        out[(sd(s,n) if s!='전남광주통합특별시' else sd(s,n), n)]=int(row[3].replace(',',''))
    return out
a=sg('200812'); b=sg('202609')
tot_a=sum(a.values()); tot_b=sum(b.values()); print('0-9 2008',tot_a,'2026',tot_b, round((tot_b/tot_a-1)*100,1))
json.dump({'S':S,'k08':{f'{k[0]}|{k[1]}':v for k,v in a.items()},'k26':{f'{k[0]}|{k[1]}':v for k,v in b.items()}},open(D+'../q19_raw.json','w'),ensure_ascii=False)
