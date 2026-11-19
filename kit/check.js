// Screenshot a page in four views and report script errors and horizontal overflow.
// usage: node kit/check.js <page.html> <outdir> [figIds comma separated]
// - The page may be an Artifact fragment (no <html>); it is wrapped in a minimal document first.
// - The page is scrolled to the bottom slowly so IntersectionObserver animations run before the shots.
// - With figure ids (e.g. f1,f2,f3), each figure is also shot on its own.
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');
(async () => {
  const [src, out, figs] = process.argv.slice(2);
  if (!src || !out) { console.error('usage: node kit/check.js <page.html> <outdir> [f1,f2]'); process.exit(1); }
  fs.mkdirSync(out, { recursive: true });
  let body = fs.readFileSync(src, 'utf8');
  if (!/<html/i.test(body)) body = '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>[hidden]{display:none!important}</style></head><body>' + body + '</body></html>';
  const wrapped = path.join(out, '_page.html'); fs.writeFileSync(wrapped, body);
  const b = await chromium.launch();
  for (const [name, w, sc] of [['desk-light', 1100, 'light'], ['desk-dark', 1100, 'dark'], ['mob-light', 400, 'light'], ['mob-dark', 400, 'dark']]) {
    const p = await b.newPage({ viewport: { width: w, height: 900 }, colorScheme: sc });
    const errs = [];
    p.on('pageerror', (e) => errs.push(String(e))); p.on('console', (m) => m.type() === 'error' && errs.push(m.text()));
    await p.goto('file://' + path.resolve(wrapped)); await p.waitForTimeout(800);
    const h = await p.evaluate(() => document.documentElement.scrollHeight);
    for (let y = 0; y < h; y += 500) { await p.evaluate((yy) => window.scrollTo(0, yy), y); await p.waitForTimeout(250); }
    await p.waitForTimeout(2500); await p.evaluate(() => window.scrollTo(0, 0));
    await p.screenshot({ path: path.join(out, `${name}.png`), fullPage: true });
    if (figs) for (const f of figs.split(',')) {
      const loc = p.locator('#' + f); if (await loc.count()) await loc.screenshot({ path: path.join(out, `${name}-${f}.png`) });
    }
    const over = await p.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    console.log(name, 'overflow', over, errs.length ? errs : 'no errors');
    await p.close();
  }
  await b.close();
})();
