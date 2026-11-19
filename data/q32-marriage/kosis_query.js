// usage: node kq.js ORG TBL spec.json
// spec.json: [{"out":"name.html","prd":"Y,2025,@","ov":{"OV_L1_ID":["11","11010"]},"itm":["T10"],"set":{"k":"v"}}, ...]
// Captures the page's own html.do POST (same session), then re-posts it with the period / class / item lists replaced.
const { chromium } = require('playwright'); const fs=require('fs');
(async () => { const [org,tbl,specF]=process.argv.slice(2); const spec=JSON.parse(fs.readFileSync(specF,'utf8'));
const b=await chromium.launch(); const p=await b.newPage(); let post=null;
p.on('request',r=>{ if(r.url().endsWith('/statHtml/html.do') && !post) post=r.postData(); });
for (let i=0;i<5 && !post;i++){ try{ await p.goto(`https://kosis.kr/statHtml/statHtml.do?orgId=${org}&tblId=${tbl}&conn_path=I2`,{timeout:90000}); await p.waitForTimeout(8000);}catch(e){} }
if(!post){ console.log('no post'); process.exit(1); }
fs.writeFileSync(`post_${tbl}.txt`,post);
for (const s of spec){ if (fs.existsSync(s.out) && fs.statSync(s.out).size>3000 && fs.readFileSync(s.out,'utf8').includes('"result"')) continue;
  const params=new URLSearchParams(post); let fl=JSON.parse(params.get('fieldList'));
  if (s.prd) fl.forEach(f=>{ if(f.targetId==='PRD') f.prdValue=s.prd; });
  if (s.itm) { fl=fl.filter(f=>f.targetId!=='ITM_ID'); s.itm.forEach(v=>fl.push({targetId:'ITM_ID',targetValue:v,prdValue:''})); }
  if (s.ov) for (const [k,vals] of Object.entries(s.ov)) { fl=fl.filter(f=>f.targetId!==k); vals.forEach(v=>fl.push({targetId:k,targetValue:v,prdValue:''})); }
  params.set('fieldList',JSON.stringify(fl)); if (s.set) for (const [k,v] of Object.entries(s.set)) params.set(k,v);
  let txt='';
  for (let k=0;k<5;k++){ txt=await p.evaluate(async (body)=>{ try{ const r=await fetch('/statHtml/html.do',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'},body}); return await r.text(); }catch(e){ return 'ERR'+e; } }, params.toString()); if(txt.includes('"result"')) break; await p.waitForTimeout(3000); }
  fs.writeFileSync(s.out,txt); console.log(s.out,txt.length,txt.includes('"result"')); }
await b.close();})();
