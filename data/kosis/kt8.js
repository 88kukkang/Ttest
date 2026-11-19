const { chromium } = require('playwright'); const fs=require('fs');
// usage: node kt6.js TBL — saves y_TBL_YYYY.html for 2018..2025
(async () => { const [org,tbl,...PRDS]=process.argv.slice(2); const b=await chromium.launch(); const p=await b.newPage(); let post=null;
p.on('request',r=>{ if(r.url().endsWith('/statHtml/html.do')) post=r.postData(); });
for (let i=0;i<4 && !post;i++){ try{ await p.goto(`https://kosis.kr/statHtml/statHtml.do?orgId=${org}&tblId=${tbl}&conn_path=I2`,{timeout:90000}); await p.waitForTimeout(8000);}catch(e){} }
if(!post){ console.log('no post'); process.exit(1); }
for (const y of PRDS){
  const params=new URLSearchParams(post); const fl=JSON.parse(params.get('fieldList')); fl[0].prdValue=`${y},@`; params.set('fieldList',JSON.stringify(fl));
  let txt='';
  for (let k=0;k<5;k++){ txt=await p.evaluate(async (body)=>{ try{ const r=await fetch('/statHtml/html.do',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'},body}); return await r.text(); }catch(e){ return 'ERR'+e; } }, params.toString()); if(txt.length>2000) break; await p.waitForTimeout(3000); }
  fs.writeFileSync(`p_${tbl}_${y.replace(",","_")}.html`,txt); console.log(tbl,y,txt.length);
}
await b.close();})();
