import csv,io,subprocess,collections,re,json
D='/tmp/claude-0/-home-user/867911d4-434e-5c1c-a4fa-95438af19a83/scratchpad/q8/'
t=subprocess.run(['iconv','-f','cp949','-t','utf-8',D+'f.bin'],capture_output=True).stdout.decode()
R=list(csv.reader(io.StringIO(t))); h=R[0]; rows=R[1:]
ix={c:i for i,c in enumerate(h)}
def g(r,*names): return sum(int(r[ix[n]] or 0) for n in names)
MF=lambda b:(b+'_남',b+'_여')
FIELDS=[('예체능',r'영상|동양화|서양화|사진|성악|기악'),('인문',r'^미학'),('자연',r'나노|신약|약자원|한약자원|의류|아동|가정|소비자|주거'),('의약',r'의예|의학|치의|한의|약학|약과학|간호|물리치료|작업치료|임상병리|방사선|치위생|치기공|응급구조|보건|안경광학|언어치료|재활|의료|요양|수의'),
('교육',r'교육|사범'),
('예체능',r'미술|음악|디자인|체육|무용|연극|영화|연기|뷰티|미용|사진|만화|애니|공예|조형|패션|스포츠|방송|실용|성악|작곡|피아노|국악|회화|조소|예술|웹툰|메이크업|헤어|네일|태권도|골프|레저|모델|K-?POP|엔터|공연|댄스|게임그래픽|제과|제빵|조리|외식|바리스타|플로리'),
('공학',r'공학|기계|전기|전자|컴퓨터|소프트웨어|건축|토목|신소재|자동차|항공|정보통신|반도체|인공지능|AI|데이터|로봇|에너지|조선|원자력|도시|게임|IT|ICT|보안|드론|모빌리티|철도|소방|메카|설비|금형|용접|정보시스템|사이버|네트워크|빅데이터|클라우드|스마트|전산|시스템|인테리어|정보처리|화공|섬유|고분자|재료|금속|세라믹|광학|해양공|환경공|산업'),
('자연',r'수학|물리|화학|생명|생물|지구|통계|식품|농|원예|동물|수산|해양|산림|환경|영양|천문|대기|지리|지질|바이오|미생물|분자|유전|축산|임학|조경|과학'),
('인문',r'국어|국문|영어|영문|일어|일본|중국|중어|불어|프랑스|독어|독일|러시아|스페인|사학|역사|철학|문학|문헌정보|신학|종교|언어|고고|한문|문예|문창|창작|불교|기독|선교|아랍|베트남|인도|글로벌|통번역|어문|교양|인문'),
('사회',r'.')]
def field(name):
    for f,rx in FIELDS:
        if re.search(rx,name): return f
agg=collections.defaultdict(lambda:collections.Counter()); maj=collections.defaultdict(lambda:collections.Counter())
def out(r):
    c=collections.Counter()
    c['grad']=g(r,*MF('졸업자'))
    c['job']=g(r,*MF('건보가입취업자'),*MF('교내취업자'),*MF('해외취업자'),*MF('농림어업종사자'))
    c['free']=g(r,*MF('개인창작활동종사자'),*MF('1인창사업자'),*MF('프리랜서'))
    c['study']=g(r,*MF('진학자'))
    c['army']=g(r,'입대자')
    c['already']=g(r,*MF('입학당시기취업자'))
    c['foreign']=g(r,*MF('외국인유학생'))
    c['excl']=g(r,*MF('취업불가능자'),*MF('제외인정자'))
    c['none']=g(r,*MF('기타'),*MF('미상'))
    return c
chk=collections.Counter()
for r in rows:
    c=out(r); f=field(r[2]); agg[f].update(c); maj[(re.sub(r'\s+','',r[2]),f)].update(c)
    s=sum(v for k,v in c.items() if k not in('grad','already')); chk['grad']+=c['grad']; chk['sum']+=s
print('check grad vs parts',chk)
for f,c in sorted(agg.items(),key=lambda x:-x[1]['grad']):
    G=c['grad']; den=G-c['study']-c['army']-c['excl']-c['foreign']-c['already']; emp=(c['job']+c['free'])/den*100
    print(f,G,{k:round(v/G*100,1) for k,v in c.items() if k!='grad'},'취업률',round(emp,1))
json.dump({'agg':agg,'maj':{f'{k[0]}|{k[1]}':v for k,v in maj.items() if v['grad']>=800}},open('raw.json','w'),ensure_ascii=False)
print(len([1 for v in maj.values() if v['grad']>=800]))
# sample unknown classification
print([k for k in maj if k[1]=='사회'][:80])
