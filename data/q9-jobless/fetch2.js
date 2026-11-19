const { chromium } = require('playwright');
// Open an EIS report, type a wider start month into its period box, run it, save the pivot JSON.
// usage: node fetch2.js <menuId> <from YYYYMM> <out.json>
(async () => {
  const [menuId, from, out, to] = process.argv.slice(2);
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1550, height: 1000 } }); const fs = require('fs');
  p.on('dialog', (d) => d.dismiss());
  let n = 0;
  await p.route(/olap\/report\/pivotSummaryMatrix\.do/, (route) => { const q = new URLSearchParams(route.request().postData() || ''); if (q.has('paging')) { const pg = JSON.parse(q.get('paging')); pg.limit = 5000; q.set('paging', JSON.stringify(pg)); } route.continue({ postData: q.toString() }); });
  p.on('response', async (r) => { if (r.url().includes('pivotSummaryMatrix')) { const t = await r.text(); n++; fs.writeFileSync(out.replace('.json', `_${n}.json`), t); console.log('saved', n, t.length); } });
  await p.goto('https://eis.work24.go.kr/eisps/opiv/selectOpivList.do', { waitUntil: 'networkidle', timeout: 90000 }).catch(e => console.log(e.message));
  await p.evaluate((m) => fn_menuMove(m, '/eisps/rpt/reptDtl.do'), menuId).catch(e => console.log('menu', e.message));
  for (let i = 0; i < 90 && n < 1; i++) await p.waitForTimeout(1000);
  const fr = p.frames().find((f) => f.url().includes('viewer.do'));
  console.log('frame', !!fr);
  const inputs = await fr.$$('input[type=text]');
  const vals = []; for (const h of inputs) vals.push([await h.getAttribute('class'), await h.inputValue(), await h.isVisible()]);
  console.log(JSON.stringify(vals).slice(0, 800));
  const first = (await Promise.all(inputs.map(async (h) => [(await h.inputValue()), h]))).find(([v]) => /^\d{6}$/.test(v));
  const dates = []; for (const h of inputs) if (/^\d{6}$/.test(await h.inputValue())) dates.push(h);
  if (to && dates[1]) { await dates[1].click({ clickCount: 3 }); await dates[1].fill(to); await dates[1].press('Enter'); await p.waitForTimeout(400); }
  if (dates[0]) { await dates[0].click({ clickCount: 3 }); await dates[0].fill(from); await dates[0].press('Enter'); await p.waitForTimeout(400); }
  p.on('dialog', (d) => console.log('dialog', d.message()));
  // click the search (돋보기) button
  const btns = await fr.$$('button, a, div[class*=search], span[class*=search], img');
  const desc = []; for (const h of btns.slice(0, 80)) desc.push(((await h.getAttribute('class')) || '') + '|' + ((await h.getAttribute('title')) || '') + '|' + ((await h.innerText().catch(() => '')) || '').slice(0, 10));
  console.log(desc.filter((d) => /search|조회|query|btn/i.test(d)).slice(0, 20).join('\n'));
  await fr.evaluate(() => document.getElementById('btn_query').click()).catch(e => console.log('click', e.message));
  for (let i = 0; i < 120 && n < 2; i++) await p.waitForTimeout(1000);
  await p.screenshot({ path: out.replace('.json', '.png') });
  await b.close();
})();
