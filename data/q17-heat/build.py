import openpyxl,json,csv,io,subprocess
D='/tmp/claude-0/-home-user/867911d4-434e-5c1c-a4fa-95438af19a83/scratchpad/q17/'
out={}
for y in range(2012,2026):
    ws=openpyxl.load_workbook(D+f'h{y}.xlsx',read_only=True).worksheets[0]
    rows=[[x for x in r if x is not None] for r in ws.iter_rows(values_only=True)]
    rows=[r for r in rows if r]
    sec=None; hdr=None; d={}
    for r in rows:
        if len(r)==1 and isinstance(r[0],str) and r[0] in ('성별','연령','보험유형','직업','질환','발생시간','발생장소'): sec=r[0]; hdr=None; continue
        if sec and r[0]=='구분': hdr=[str(x).replace('\n','').strip() for x in r[1:]]; continue
        if sec=='발생장소' and r[0]=='소계': sub=[str(x).replace('\n','').strip() for x in r]; continue
        if sec and r[0]=='인원(명)':
            vals=[float(str(x).replace(',','')) for x in r[1:]]
            if sec=='발생장소':
                names=['합계','실외']+['실외:'+s for s in sub[1:9]]+['실내']+['실내:'+s for s in sub[10:]]
                d[sec]=dict(zip(names,vals))
            else: d[sec]=dict(zip(hdr,vals))
    out[y]=d
for y in (2012,2018,2025): print(y,out[y].get('발생장소'),out[y]['연령'])
def pop(y):
    t=subprocess.run(['iconv','-f','cp949','-t','utf-8',D+f'pop_{y}_1.csv'],capture_output=True).stdout.decode()
    r=list(csv.reader(io.StringIO(t))); h=r[0]; v=[int(x.replace(',','')) for x in r[1][1:]]
    return {c.split('_')[-1]:v[i] for i,c in enumerate(h[1:])}
P={y:pop(y) for y in (2014,2018,2025)}
print(P[2025])
json.dump({'y':out,'pop':P},open('/tmp/claude-0/-home-user/867911d4-434e-5c1c-a4fa-95438af19a83/scratchpad/q17_raw.json','w'),ensure_ascii=False)
for y in range(2012,2026): print(y,out[y]['성별']['합계'],out[y]['직업'].get('단순노무종사자'),out[y]['직업'].get('농림어업숙련종사자'),out[y]['직업'].get('무직(노숙인제외)'), out[y]['연령'].get('65+'))
