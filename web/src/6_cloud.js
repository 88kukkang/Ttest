
// =====================================================================
// 키워드 클라우드 탭
// =====================================================================
function wordDetail(prefix, D, term, sel, opts) {
  // 클라우드·관계도 공용: 월별 막대 + 최근 보도자료
  const { dept, from, to } = opts;
  const ti = D.termIndex.get(term);
  const pool = D.docs.filter((d) => (dept === "" || d.dept === +dept) && d.termSet.has(ti));
  const inSel = pool.filter((d) => (!from || d.month >= from) && (!to || d.month <= to));
  const box = $(prefix + "-chart");
  if (box) {
    const counts = D.months.map((m) => pool.filter((d) => d.month === m).length);
    const W = Math.max(240, box.clientWidth), H = 110, mt = 16, mb = 18, ih = H - mt - mb;
    const band = W / D.months.length, bw = Math.min(24, band * 0.66);
    const max = Math.max(1, ...counts), maxI = counts.indexOf(max);
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": `${term} 월별 보도자료 수` });
    svgEl("line", { x1: 0, x2: W, y1: mt + ih, y2: mt + ih, class: "base" }, svg);
    D.months.forEach((m, i) => {
      const cx = band * i + band / 2, h = (counts[i] / max) * ih, y = mt + ih - h;
      const on = (!from || m >= from) && (!to || m <= to);
      const hit = svgEl("rect", { x: band * i, y: 0, width: band, height: mt + ih, class: "hit", tabindex: 0, "aria-label": `${monthLabel(m)} ${counts[i]}건` }, svg);
      svgEl("path", { class: "mark", d: colPath(cx - bw / 2, y, bw, h, 4), style: `fill:var(${on ? "--bar" : "--bar-dim"})` }, svg);
      bindHover(hit, () => fillTip(`${term} · ${monthLabel(m)}${m === PARTIAL ? " (이틀치)" : ""}`, [{ value: `${counts[i]}건` }]));
    });
    svgText(svg, 0, H - 4, tickLabel(D.months[0], true));
    svgText(svg, W, H - 4, tickLabel(D.months[D.months.length - 1], true), { "text-anchor": "end" });
    svgText(svg, band * maxI + band / 2, mt - 4, String(max), { "text-anchor": "middle", class: "val num" });
    box.replaceChildren(svg);
  }
  $(prefix + "-docs-title").textContent = `‘${term}’이(가) 나온 고른 범위의 보도자료 (${fmt(inSel.length)}건 중 최근 ${Math.min(6, inSel.length)}건)`;
  const ul = $(prefix + "-docs"); ul.replaceChildren();
  for (const d of inSel.slice(0, 6)) {
    const li = el("li");
    li.append(el("span", "d-meta num", `${dateLabel(d.date)} · ${D.depts[d.dept] || "부서 미상"}`), articleLink(d, [term.toLowerCase()]));
    ul.appendChild(li);
  }
  return inSel.length;
}
function fillCloudFilters(prefix, D) {
  fillMonthSelects(prefix + "-from", prefix + "-to", D.months);
  const dsel = $(prefix + "-dept");
  dsel.options[0].textContent = `전체 부서 (${D.deptCounts.length})`;
  for (const [i, n] of D.deptCounts) dsel.appendChild(new Option(`${D.depts[i] || "부서 미상"} (${n})`, String(i)));
}

const C = (() => {
  let D = null, words = [], sel = [], picked = null, drawSeq = 0, started = false, dirty = true;
  function compute() {
    const from = $("c-from").value, to = $("c-to").value, dept = $("c-dept").value;
    sel = D.docs.filter((d) => (!from || d.month >= from) && (!to || d.month <= to) && (dept === "" || d.dept === +dept));
    const df = new Uint32Array(D.terms.length);
    for (const d of sel) for (const t of d.terms) df[t]++;
    const filtered = sel.length !== D.docs.length;
    let basis = $("c-basis").value;
    const note = $("c-note"); note.hidden = true;
    if (basis === "z" && !filtered) { basis = "df"; note.textContent = "‘두드러진 말’은 기간이나 부서를 골라야 비교할 대상이 생깁니다. 지금은 많이 나온 말로 그렸습니다."; note.hidden = false; }
    const n = Math.max(1, sel.length), scored = [];
    if (basis === "df") { for (let i = 0; i < df.length; i++) if (df[i] > 0) scored.push({ i, df: df[i], score: df[i] }); }
    else {
      let nT = 0, nR = 0, pooled = 0;
      for (let i = 0; i < df.length; i++) { nT += df[i]; nR += D.totalDf[i] - df[i]; pooled += D.totalDf[i]; }
      const prior = 500;
      for (let i = 0; i < df.length; i++) {
        if (df[i] < 3) continue;
        const a = (prior * D.totalDf[i]) / pooled, yT = df[i], yR = D.totalDf[i] - df[i];
        const z = (Math.log((yT + a) / (nT + prior - yT - a)) - Math.log((yR + a) / (nR + prior - yR - a))) / Math.sqrt(1 / (yT + a) + 1 / (yR + a));
        if (z > 0) scored.push({ i, df: df[i], score: z });
      }
    }
    scored.sort((a, b) => b.score - a.score || b.df - a.df);
    words = scored.slice(0, +$("c-topn").value).map((w) => ({ ...w, term: D.terms[w.i], share: w.df / n }));
    const parts = [`보도자료 ${fmt(sel.length)}건`, `단어 ${fmt(words.length)}개`];
    if (from || to) parts.push(`${from ? monthLabel(from) : "처음"} ~ ${to ? monthLabel(to) : "끝"}`);
    if (dept !== "") parts.push(D.depts[+dept] || "부서 미상");
    $("c-meta").textContent = parts.join(" · ");
    const t = table(["순위", "단어", "보도자료 수", "비율", ...(basis === "z" ? ["z값"] : [])],
      words.map((w, r) => [String(r + 1), w.term, fmt(w.df), pct(w.share), ...(basis === "z" ? [w.score.toFixed(1)] : [])]), "data left2");
    $("c-table").replaceChildren(t);
  }
  function hash(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
  function draw() {
    const canvas = $("c-canvas");
    if (!window.WordCloud || !WordCloud.isSupported) { $("c-drawing").hidden = false; $("c-drawing").textContent = "이 브라우저에서는 클라우드를 그릴 수 없습니다. 아래 ‘표로 보기’를 이용하세요."; return; }
    const cssW = Math.max(280, $("c-stage").clientWidth - 24);
    const cssH = Math.round(Math.max(320, Math.min(620, cssW * 0.62)));
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(cssW * dpr); canvas.height = Math.round(cssH * dpr); canvas.style.height = cssH + "px";
    const many = words.length > 120;
    const maxPx = Math.max(30, Math.min(80, cssW * (many ? 0.07 : 0.085))), minPx = many ? 10 : 12;
    const vals = words.map((w) => w.score), hi = Math.max(...vals), lo = Math.min(...vals);
    const size = (v) => minPx + (maxPx - minPx) * Math.sqrt(hi === lo ? 1 : (v - lo) / (hi - lo));
    const multi = $("c-palette").value === "multi";
    const wc = [1, 2, 3, 4, 5, 6, 7, 8].map((k) => css(`--w${k}`)), qc = [css("--q1"), css("--q2"), css("--q3")];
    const colorOf = new Map(words.map((w, r) => [w.term, multi ? wc[hash(w.term) % 8] : qc[r < words.length * 0.1 ? 0 : r < words.length * 0.4 ? 1 : 2]]));
    const byTerm = new Map(words.map((w) => [w.term, w]));
    const seq = ++drawSeq;
    $("c-drawing").hidden = false; $("c-drawing").textContent = "그리는 중…";
    canvas.addEventListener("wordcloudstop", () => { if (seq === drawSeq) $("c-drawing").hidden = true; }, { once: true });
    WordCloud(canvas, {
      list: words.map((w) => [w.term, size(w.score)]),
      weightFactor: (s) => s * dpr,
      fontFamily: '"Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif',
      fontWeight: (word, weight) => (weight >= maxPx * 0.45 ? "700" : "500"),
      color: (word) => colorOf.get(word),
      backgroundColor: "rgba(0,0,0,0)",
      gridSize: Math.round((many ? 7 : 9) * dpr), // 낱말 사이 간격: 좁으면 이웃 단어가 붙어 복합어처럼 읽힌다
      rotateRatio: 0, shape: "circle", ellipticity: Math.min(1, cssH / cssW + 0.05),
      shuffle: false, shrinkToFit: true, drawOutOfBound: false,
      hover: (item, dim, evt) => {
        canvas.style.cursor = item ? "pointer" : "default";
        if (!item) return hideTip();
        const w = byTerm.get(item[0]);
        showTip(w.term, `${fmt(w.df)}건 (${pct(w.share)})`, evt.clientX, evt.clientY);
      },
      click: (item) => { if (item) pick(item[0]); },
    });
    dirty = false;
  }
  function pick(term) {
    picked = term;
    const opts = { dept: $("c-dept").value, from: $("c-from").value, to: $("c-to").value };
    $("c-term").textContent = term;
    const n = wordDetail("c", D, term, sel, opts);
    $("c-figs").textContent = `고른 범위 보도자료 ${fmt(sel.length)}건 중 ${fmt(n)}건 (${pct(n / Math.max(1, sel.length))})`;
    const act = $("c-actions"); act.replaceChildren();
    const b1 = el("button", "btn-ghost", "이 단어로 검색"); b1.type = "button"; b1.addEventListener("click", () => { S.query(term); Tabs.show("search"); });
    const b2 = el("button", "btn-ghost", "관계도에서 보기"); b2.type = "button"; b2.addEventListener("click", () => { N.center(term); Tabs.show("network"); });
    act.append(b1, b2);
  }
  function refresh() {
    hideTip(); compute(); draw();
    const keep = picked && words.some((w) => w.term === picked) ? picked : words[0] && words[0].term;
    if (keep) pick(keep);
  }
  async function start() {
    started = true;
    $("c-meta").textContent = "불러오는 중…";
    try { D = await cloudReady(); } catch (e) { $("c-meta").textContent = `불러오지 못했습니다 (${e.message}).`; return; }
    fillCloudFilters("c", D);
    try { await document.fonts.load('700 40px "Noto Sans KR"'); await document.fonts.load('500 16px "Noto Sans KR"'); } catch {}
    for (const id of ["c-from", "c-to", "c-dept", "c-basis", "c-topn"]) $(id).addEventListener("change", refresh);
    $("c-palette").addEventListener("change", () => { hideTip(); draw(); });
    $("c-canvas").addEventListener("mouseleave", hideTip);
    $("c-copy").addEventListener("click", () => {
      const src = $("c-canvas"), out = document.createElement("canvas");
      out.width = src.width; out.height = src.height;
      const ctx = out.getContext("2d"); ctx.fillStyle = css("--paper"); ctx.fillRect(0, 0, out.width, out.height); ctx.drawImage(src, 0, 0);
      try {
        navigator.clipboard.write([new ClipboardItem({ "image/png": new Promise((res) => out.toBlob(res, "image/png")) })])
          .then(() => toast("클라우드 이미지를 복사했습니다. 문서나 메신저에 붙여넣으면 됩니다."), () => toast("이 화면에서는 이미지 복사가 막혀 있습니다. 화면 캡처를 이용해 주세요."));
      } catch { toast("이 화면에서는 이미지 복사가 막혀 있습니다. 화면 캡처를 이용해 주세요."); }
    });
    refresh();
  }
  return {
    init() {},
    show() { if (!started) start(); else if (dirty) { draw(); if (picked) pick(picked); } },
    resize() { if (D) { draw(); if (picked) pick(picked); } },
    themeChanged() { dirty = true; },
  };
})();
