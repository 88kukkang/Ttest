// Quick audit: small targets, low-contrast text (HTML and SVG), focusable SVGs, reduced-motion behaviour.
const { chromium } = require('playwright');
(async () => {
  const [page, theme, w] = process.argv.slice(2);
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: +w || 400, height: 900 }, colorScheme: theme || 'light', reducedMotion: 'reduce' });
  await p.goto("file://" + require("path").resolve(page)); await p.waitForTimeout(1200);
  const r = await p.evaluate(() => {
    const lum = (c) => { const m = c.match(/[\d.]+/g).map(Number); const f = (v) => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }; return .2126 * f(m[0]) + .7152 * f(m[1]) + .0722 * f(m[2]); };
    const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05); };
    const bgOf = (el) => { while (el) { if (el.tagName === 'rect' && el.getAttribute('fill') && !el.getAttribute('fill').includes('url')) { const c = getComputedStyle(el).fill; if (c && c.startsWith('rgb')) return c; } const c = getComputedStyle(el).backgroundColor; if (c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') return c; el = el.parentElement; } return 'rgb(255,255,255)'; };
    const small = [...document.querySelectorAll('button, a, input, summary, [tabindex="0"]')].filter((e) => { const b = e.getBoundingClientRect(); return b.width > 0 && (b.height < 24 || b.width < 24); }).map((e) => e.tagName + '.' + e.className + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height) + ' ' + (e.textContent || '').trim().slice(0, 20));
    const low = [];
    document.querySelectorAll('p, li, dd, dt, td, th, span, summary, figcaption, button, h1, h2, h3, div.yr, text').forEach((e) => {
      if (e.tagName !== 'text' && [...e.childNodes].every((n) => n.nodeType !== 3 || !n.textContent.trim())) return;
      const cs = getComputedStyle(e); const fg = e.tagName === 'text' ? cs.fill : cs.color; if (!fg || !fg.startsWith('rgb')) return;
      let bg; if (e.tagName === 'text') { const svg = e.closest('svg'); bg = bgOf(svg.parentElement); } else bg = bgOf(e);
      const rt = ratio(fg, bg), size = parseFloat(cs.fontSize) * (e.tagName === 'text' ? (e.closest('svg').getBoundingClientRect().width / e.closest('svg').viewBox.baseVal.width || 1) : 1);
      const need = size >= 18.6 || (size >= 14 && +cs.fontWeight >= 700) ? 3 : 4.5;
      if (rt < need) low.push(`${e.tagName}.${e.getAttribute('class') || ''} ${rt.toFixed(2)} (${need}) size ${size.toFixed(1)} "${e.textContent.trim().slice(0, 18)}"`);
      if (size < 11 && e.textContent.trim()) low.push(`TINY ${e.tagName}.${e.getAttribute('class') || ''} ${size.toFixed(1)}px "${e.textContent.trim().slice(0, 18)}"`);
    });
    const svgs = [...document.querySelectorAll('figure svg[role=img]')].map((s) => (s.getAttribute('tabindex') ? 'tab ' : 'NOTAB ') + (s.getAttribute('aria-label') || '').slice(0, 40));
    const heads = [...document.querySelectorAll('h1,h2,h3')].map((h) => h.tagName).join('');
    return { small: [...new Set(small)].slice(0, 20), low: [...new Set(low)].slice(0, 40), svgs, heads, lang: document.documentElement.lang };
  });
  console.log(JSON.stringify(r, null, 1));
  await b.close();
})();
