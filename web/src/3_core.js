(() => {
"use strict";
// =====================================================================
// 공용 도구
// =====================================================================
const ARTICLE = "https://www.mois.go.kr/frt/bbs/type010/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000008&nttId=";
const PARTIAL = "2026-10";
const NS = "http://www.w3.org/2000/svg";
const $ = (id) => document.getElementById(id);
const fmt = (n) => Number(n).toLocaleString("ko-KR");
const pct = (x) => (x * 100).toFixed(x > 0 && x < 0.1 ? 1 : 0) + "%";
const monthLabel = (m) => { const [y, mo] = m.split("-"); return `${y}년 ${+mo}월`; };
const dateLabel = (d) => { const [y, m, dd] = d.split("-"); return `${y}. ${+m}. ${+dd}.`; };
const tickLabel = (m, first) => { const [y, mo] = m.split("-"); return first || mo === "01" ? `${y.slice(2)}.${+mo}` : `${+mo}`; };
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function svgEl(tag, attrs, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function svgText(parent, x, y, str, attrs = {}) { const t = svgEl("text", { x, y, ...attrs }, parent); t.textContent = str; return t; }
function colPath(x, y, w, h, r) { if (h <= 0) return ""; r = Math.min(r, w / 2, h); return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`; }
const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch {} } };
function toast(msg) { const t = $("toast"); t.textContent = msg; t.hidden = false; clearTimeout(toast.h); toast.h = setTimeout(() => (t.hidden = true), 2600); }
function table(headers, rows, cls = "data") {
  const t = el("table", cls);
  const hr = t.createTHead().insertRow();
  for (const x of headers) hr.appendChild(el("th", null, x));
  const tb = t.createTBody();
  for (const r of rows) { const tr = tb.insertRow(); for (const c of r) tr.insertCell().textContent = c; }
  return t;
}
/** 보도자료 제목 링크: 누르면 페이지 안 읽기 창으로 본문, Ctrl/⌘/가운데 클릭은 행안부 원문 */
function articleLink(d, terms = [], content = null) {
  const a = el("a"); a.href = ARTICLE + d.id; a.target = "_blank"; a.rel = "noopener";
  a.appendChild(content || document.createTextNode(d.title));
  a.addEventListener("click", (e) => { if (e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return; e.preventDefault(); Reader.open(d.id, terms); });
  return a;
}
const Reader = (() => {
  const dlg = $("reader");
  $("reader-close").addEventListener("click", () => dlg.close());
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
  async function open(id, terms = []) {
    await docsReady;
    const d = DOC_BY_ID.get(String(id));
    if (!d) { window.open(ARTICLE + id, "_blank", "noopener"); return; }
    $("reader-meta").textContent = `${dateLabel(d.date)} · ${d.dept || "부서 미상"} · 본문 ${fmt(d.body.length)}자`;
    $("reader-title").textContent = d.title;
    $("reader-orig").href = ARTICLE + d.id;
    const body = $("reader-body");
    body.replaceChildren(terms.length ? highlighted(d.body, d.lb, terms) : document.createTextNode(d.body));
    hideTip();
    if (typeof dlg.showModal === "function") { if (!dlg.open) dlg.showModal(); } else dlg.setAttribute("open", "");
    body.scrollTop = 0;
    const first = body.querySelector("mark");
    if (first) first.scrollIntoView({ block: "center" });
  }
  return { open };
})();
/** 본문 안 행안부 원문 링크(nttId=…)를 읽기 창으로 연다 (AI 답변용) */
function routeArticleClicks(container, termsFn = () => []) {
  container.addEventListener("click", (e) => {
    const a = e.target.closest && e.target.closest("a[href]");
    if (!a || e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
    const m = a.href.match(/[?&]nttId=(\d+)/);
    if (!m || !a.href.startsWith("https://www.mois.go.kr/")) return;
    e.preventDefault();
    Reader.open(m[1], termsFn());
  });
}

// ---- 툴팁: 값이 굵게, 이름은 보조 ----
const tip = $("tip");
function fillTip(title, rows) {
  tip.replaceChildren(el("div", "t", title));
  for (const r of rows) {
    const row = el("div", "t-row");
    if (r.color) { const k = el("span", "key"); k.style.borderTopColor = r.color; row.appendChild(k); }
    row.appendChild(el("b", null, r.value));
    if (r.label) row.appendChild(el("span", null, r.label));
    tip.appendChild(row);
  }
  tip.hidden = false;
}
function placeTip(x, y) {
  const w = tip.offsetWidth, h = tip.offsetHeight;
  let left = x + 14, top = y - h - 12;
  if (left + w > innerWidth - 8) left = x - w - 14;
  if (top < 8) top = y + 18;
  tip.style.left = Math.max(8, left) + "px"; tip.style.top = top + "px";
}
function showTip(title, value, x, y) { fillTip(title, [{ value }]); placeTip(x, y); }
const hideTip = () => (tip.hidden = true);
function bindHover(node, content) {
  node.addEventListener("pointermove", (e) => { content(); placeTip(e.clientX, e.clientY); });
  node.addEventListener("pointerleave", hideTip);
  node.addEventListener("focus", () => { const b = node.getBoundingClientRect(); content(); placeTip(b.left + b.width / 2, b.top); });
  node.addEventListener("blur", hideTip);
}

// ---- 월 선택 상자 채우기 ----
function fillMonthSelects(fromId, toId, months) {
  for (const id of [fromId, toId]) {
    const s = $(id);
    s.replaceChildren(new Option(id === fromId ? "처음부터" : "끝까지", ""));
    for (const m of months) s.appendChild(new Option(monthLabel(m), m));
  }
}

// =====================================================================
// 데이터: 페이지와 함께 올린 base64(gzip(JSON)) 파일
// =====================================================================
async function fetchB64Json(name) {
  const res = await fetch(name);
  if (!res.ok) throw new Error(`${name}: HTTP ${res.status}`);
  const bin = atob((await res.text()).trim());
  const buf = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
  return JSON.parse(await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream("gzip"))).text());
}
let DOCS = [], DOC_BY_ID = new Map(), MONTHS = [], DEPT_COUNTS = [];
const docsReady = fetchB64Json("docs.b64.txt").then((raw) => {
  DOCS = raw.docs.map(([id, date, dept, title, body]) => ({ id, date, month: date.slice(0, 7), dept, title, body, lt: title.toLowerCase(), lb: body.toLowerCase() }));
  DOC_BY_ID = new Map(DOCS.map((d) => [d.id, d]));
  MONTHS = [...new Set(DOCS.map((d) => d.month))].sort();
  const cnt = new Map();
  for (const d of DOCS) cnt.set(d.dept, (cnt.get(d.dept) || 0) + 1);
  DEPT_COUNTS = [...cnt].sort((a, b) => b[1] - a[1]);
  document.querySelectorAll(".js-total").forEach((n) => (n.textContent = fmt(DOCS.length)));
  const lastDate = DOCS.reduce((a, d) => (d.date > a ? d.date : a), "");
  document.querySelectorAll(".js-last").forEach((n) => (n.textContent = dateLabel(lastDate)));
});
let cloudPromise = null, CLOUD = null;
function cloudReady() {
  return (cloudPromise ||= fetchB64Json("cloud.b64.txt").then((raw) => {
    const docs = raw.docs.map(([id, date, dept, title, terms]) => ({ id, date, month: date.slice(0, 7), dept, title, terms, termSet: new Set(terms) }));
    const totalDf = new Uint32Array(raw.terms.length);
    for (const d of docs) for (const t of d.terms) totalDf[t]++;
    const months = [...new Set(docs.map((d) => d.month))].sort();
    const cnt = new Map();
    for (const d of docs) cnt.set(d.dept, (cnt.get(d.dept) || 0) + 1);
    CLOUD = { terms: raw.terms, depts: raw.depts, docs, totalDf, months, termIndex: new Map(raw.terms.map((t, i) => [t, i])), deptCounts: [...cnt].sort((a, b) => b[1] - a[1]) };
    return CLOUD;
  }));
}

// =====================================================================
// 검색 엔진 (검색 탭과 AI 도구가 함께 씀)
// =====================================================================
function countOcc(s, t) { let n = 0, i = s.indexOf(t); while (i !== -1) { n++; i = s.indexOf(t, i + t.length); } return n; }
function parseQuery(q) {
  q = q.replace(/[“”]/g, '"');
  const terms = [], excludes = [];
  const re = /(-?)"([^"]+)"|(-?)(\S+)/g;
  let m;
  while ((m = re.exec(q))) {
    const neg = m[1] || m[3];
    const t = (m[2] != null ? m[2] : m[4] || "").toLowerCase().trim();
    if (!t || t === "-") continue;
    (neg ? excludes : terms).push(t);
  }
  return { terms, excludes };
}
/** all: 모두 포함, any: 하나 이상 포함, none: 제외. 점수 = 본문 등장 수 + 제목 등장 수 × 5 */
function findDocs({ all = [], any = [], none = [], from = "", to = "", dept = "", deptLike = "", scope = "all" }) {
  const out = [];
  for (const d of DOCS) {
    if (from && d.month < from) continue;
    if (to && d.month > to) continue;
    if (dept && d.dept !== dept) continue;
    if (deptLike && !d.dept.includes(deptLike)) continue;
    let ok = true, score = 0, hits = 0;
    for (const t of all) {
      const a = countOcc(d.lt, t), b = scope === "title" ? 0 : countOcc(d.lb, t);
      if (!a && !b) { ok = false; break; }
      score += b + a * 5; hits += a + b;
    }
    if (!ok) continue;
    if (any.length) {
      let anyHit = false;
      for (const t of any) {
        const a = countOcc(d.lt, t), b = scope === "title" ? 0 : countOcc(d.lb, t);
        if (a || b) { anyHit = true; score += b + a * 5; hits += a + b; }
      }
      if (!anyHit) continue;
    }
    if (none.length) {
      const hay = scope === "title" ? d.lt : d.lt + "\n" + d.lb;
      if (none.some((t) => hay.includes(t))) continue;
    }
    out.push({ d, score, hits });
  }
  return out;
}
function matchRanges(lower, terms) {
  const rs = [];
  for (const t of terms) { if (!t) continue; let i = lower.indexOf(t); while (i !== -1) { rs.push([i, i + t.length]); i = lower.indexOf(t, i + t.length); } }
  rs.sort((a, b) => a[0] - b[0]);
  const out = [];
  for (const r of rs) { const last = out[out.length - 1]; if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1]); else out.push(r.slice()); }
  return out;
}
function highlighted(text, lower, terms, start = 0, end = text.length) {
  const frag = document.createDocumentFragment();
  let pos = start;
  for (const [a, b] of matchRanges(lower.slice(start, end), terms)) {
    const s = a + start, e = b + start;
    if (s > pos) frag.appendChild(document.createTextNode(text.slice(pos, s)));
    frag.appendChild(el("mark", null, text.slice(s, e)));
    pos = e;
  }
  if (pos < end) frag.appendChild(document.createTextNode(text.slice(pos, end)));
  return frag;
}
function snippetWindows(d, terms, max = 3, pad = 48) {
  const wins = [];
  for (const [a, b] of matchRanges(d.lb, terms)) {
    const s = Math.max(0, a - pad), e = Math.min(d.body.length, b + pad);
    const last = wins[wins.length - 1];
    if (last && s <= last[1]) last[1] = Math.max(last[1], e); else wins.push([s, e]);
    if (wins.length > max) break;
  }
  return wins.slice(0, max);
}
function plainSnippet(d, terms, pad = 90) {
  const [w] = snippetWindows(d, terms, 1, pad);
  const [s, e] = w || [0, Math.min(d.body.length, pad * 2)];
  return (s > 0 ? "…" : "") + d.body.slice(s, e).replace(/\s+/g, " ") + (e < d.body.length ? "…" : "");
}
