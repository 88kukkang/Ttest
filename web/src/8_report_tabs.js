
// =====================================================================
// 분석 보고서 탭 (ci/build_report.py 로 만든 고정 분석, 페이지 안 JSON)
// =====================================================================
const R = (() => {
  const RD = JSON.parse($("report-data").textContent);
  // 보고서 마지막 날이 달 중간이면 그 달은 덜 찬 달
  const [ly, lm, ld] = RD.last.split("-").map(Number);
  const PARTIAL = ld < new Date(ly, lm, 0).getDate() ? RD.last.slice(0, 7) : "", PNOTE = `${ld}일까지`;
  const plabel = (m) => (m === PARTIAL ? ` (${PNOTE})` : "");
  const GOV_M = (RD.gov_start || "").slice(0, 7); // 출범한 달: 시간 차트에 세로 점선
  /** 막대 차트: 출범한 달 막대의 왼쪽 경계에 점선과 '출범' 표시 */
  function govMarker(svg, x, y1, y2, label = true) {
    svgEl("line", { x1: x, x2: x, y1, y2, class: "gov-mark" }, svg);
    if (label) svgText(svg, x + 4, y1 + 10, "이재명 정부 출범", { class: "gov-label" });
  }
  const SHIFT = [{ k: "지방정부", v: "--s1" }, { k: "지자체", v: "--s2" }, { k: "지방자치단체", v: "--s3" }];
  const shiftData = SHIFT.map((s) => ({ ...s, pts: RD.term_shift[s.k].filter((p) => p.m !== PARTIAL) }));
  let built = false;
  function volume() {
    const box = $("r-volume");
    const W = Math.max(280, box.clientWidth), H = 220, m = { l: 34, r: 8, t: 22, b: 26 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b, data = RD.monthly_counts, n = data.length;
    const yMax = Math.ceil(Math.max(...data.map((d) => d.n)) / 50) * 50;
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": "월별 보도자료 수" });
    for (let v = 0; v <= yMax; v += 50) {
      const y = m.t + ih - (v / yMax) * ih;
      svgEl("line", { x1: m.l, x2: W - m.r, y1: y, y2: y, class: v === 0 ? "base" : "grid" }, svg);
      svgText(svg, m.l - 6, y + 4, String(v), { "text-anchor": "end", class: "num" });
    }
    const band = iw / n, bw = Math.min(24, band * 0.62), step = band < 30 ? 2 : 1;
    const maxI = data.reduce((a, d, i) => (d.n > data[a].n ? i : a), 0);
    data.forEach((d, i) => {
      const cx = m.l + band * i + band / 2, hh = (d.n / yMax) * ih, y = m.t + ih - hh, partial = d.m === PARTIAL;
      if (d.m === GOV_M && i > 0) govMarker(svg, m.l + band * i, m.t - 14, m.t + ih);
      const hit = svgEl("rect", { x: m.l + band * i, y: m.t, width: band, height: ih, class: "hit", tabindex: 0, "aria-label": `${monthLabel(d.m)} ${d.n}건` }, svg);
      svgEl("path", { d: colPath(cx - bw / 2, y, bw, hh, 4), class: "mark", style: `fill:var(${partial ? "--bar-partial" : "--bar"})` }, svg);
      bindHover(hit, () => fillTip(monthLabel(d.m) + plabel(d.m), [{ value: fmt(d.n) + "건" }]));
      if (i % step === 0) svgText(svg, cx, H - 8, tickLabel(d.m, i === 0), { "text-anchor": "middle" });
      if (i === maxI) svgText(svg, cx, y - 6, String(d.n), { "text-anchor": "middle", class: "val num" });
    });
    box.replaceChildren(svg);
  }
  function shift() {
    const box = $("r-shift");
    const W = Math.max(280, box.clientWidth), H = 260, m = { l: 38, r: 76, t: 14, b: 26 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const months = shiftData[0].pts.map((p) => p.m), n = months.length;
    const yMax = Math.max(0.2, Math.ceil(Math.max(...shiftData.flatMap((s) => s.pts.map((p) => p.s))) / 0.2 - 1e-9) * 0.2);
    const X = (i) => m.l + (i / (n - 1)) * iw, Y = (s) => m.t + ih - (s / yMax) * ih;
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": "지방정부·지자체·지방자치단체 표기 비율" });
    for (let v = 0; v <= yMax + 1e-9; v += 0.2) {
      svgEl("line", { x1: m.l, x2: m.l + iw, y1: Y(v), y2: Y(v), class: v === 0 ? "base" : "grid" }, svg);
      svgText(svg, m.l - 6, Y(v) + 4, Math.round(v * 100) + "%", { "text-anchor": "end", class: "num" });
    }
    const step = iw / (n - 1) < 32 ? 2 : 1;
    months.forEach((mm, i) => { if (i % step === 0) svgText(svg, X(i), H - 8, tickLabel(mm, i === 0), { "text-anchor": "middle" }); });
    const gi = months.indexOf(GOV_M);
    if (gi > 0) govMarker(svg, (X(gi - 1) + X(gi)) / 2, m.t, m.t + ih);
    const cross = svgEl("line", { y1: m.t, y2: m.t + ih, class: "base", visibility: "hidden" }, svg);
    for (const s of shiftData) svgEl("polyline", { points: s.pts.map((p, i) => `${X(i)},${Y(p.s)}`).join(" "), fill: "none", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round", style: `stroke:var(${s.v})` }, svg);
    for (const s of shiftData) svgEl("circle", { cx: X(n - 1), cy: Y(s.pts[n - 1].s), r: 4, "stroke-width": 2, style: `fill:var(${s.v});stroke:var(--paper)` }, svg);
    svgText(svg, X(n - 1) + 9, Y(shiftData[0].pts[n - 1].s) + 4, `${shiftData[0].k} ${pct(shiftData[0].pts[n - 1].s)}`, { class: "val" });
    const dots = shiftData.map((s) => svgEl("circle", { r: 4, "stroke-width": 2, visibility: "hidden", style: `fill:var(${s.v});stroke:var(--paper)` }, svg));
    const overlay = svgEl("rect", { x: m.l - 6, y: m.t, width: iw + 12, height: ih, class: "hit", tabindex: 0, "aria-label": "월을 고르려면 좌우 화살표" }, svg);
    let idx = n - 1;
    const showAt = (i, cx, cy) => {
      idx = Math.max(0, Math.min(n - 1, i));
      cross.setAttribute("x1", X(idx)); cross.setAttribute("x2", X(idx)); cross.setAttribute("visibility", "visible");
      shiftData.forEach((s, j) => { dots[j].setAttribute("cx", X(idx)); dots[j].setAttribute("cy", Y(s.pts[idx].s)); dots[j].setAttribute("visibility", "visible"); });
      fillTip(`${monthLabel(months[idx])} · 보도자료 ${shiftData[0].pts[idx].n}건`, shiftData.map((s) => ({ color: `var(${s.v})`, value: pct(s.pts[idx].s), label: `${s.k} (${s.pts[idx].k}건)` })));
      placeTip(cx, cy);
    };
    const hide = () => { cross.setAttribute("visibility", "hidden"); dots.forEach((d) => d.setAttribute("visibility", "hidden")); hideTip(); };
    overlay.addEventListener("pointermove", (e) => { const r = svg.getBoundingClientRect(); const px = ((e.clientX - r.left) / r.width) * W; showAt(Math.round(((px - m.l) / iw) * (n - 1)), e.clientX, e.clientY); });
    overlay.addEventListener("pointerleave", hide);
    overlay.addEventListener("blur", hide);
    const keyShow = () => { const r = svg.getBoundingClientRect(); showAt(idx, r.left + (X(idx) / W) * r.width, r.top + 20); };
    overlay.addEventListener("focus", keyShow);
    overlay.addEventListener("keydown", (e) => { if (e.key === "ArrowLeft" || e.key === "ArrowRight") { e.preventDefault(); idx += e.key === "ArrowLeft" ? -1 : 1; idx = Math.max(0, Math.min(n - 1, idx)); keyShow(); } });
    box.replaceChildren(svg);
  }
  function topics() {
    const wrap = $("r-topics"); wrap.replaceChildren();
    for (const t of RD.topics) {
      const pts = t.series.filter((p) => p.m !== PARTIAL), n = pts.length;
      const card = el("div", "mini"), head = el("div", "mini-head"), chart = el("div", "chart");
      head.append(el("h4", null, t.name), el("span", "num", `${fmt(t.total)}건`));
      const peakI = pts.reduce((a, p, i) => (p.s > pts[a].s ? i : a), 0), peak = pts[peakI];
      card.append(head, chart, el("p", "mini-peak num", `최고 ${monthLabel(peak.m)} · ${pct(peak.s)} (${peak.k}건)`));
      wrap.appendChild(card);
      const W = Math.max(160, chart.clientWidth), H = 76, mt = 6, mb = 18, ih = H - mt - mb, band = W / n, bw = Math.min(24, band * 0.68), max = peak.s || 1;
      const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": `${t.name} 월별 언급 비율` });
      svgEl("line", { x1: 0, x2: W, y1: mt + ih, y2: mt + ih, class: "base" }, svg);
      pts.forEach((p, i) => {
        const cx = band * i + band / 2, hh = (p.s / max) * ih, y = mt + ih - hh;
        if (p.m === GOV_M && i > 0) govMarker(svg, band * i, mt - 4, mt + ih, false);
        const hit = svgEl("rect", { x: band * i, y: 0, width: band, height: H - mb, class: "hit", tabindex: 0, "aria-label": `${monthLabel(p.m)} ${p.k}건, ${pct(p.s)}` }, svg);
        svgEl("path", { d: colPath(cx - bw / 2, y, bw, hh, 4), class: "mark", style: "fill:var(--bar)" }, svg);
        bindHover(hit, () => fillTip(`${t.name} · ${monthLabel(p.m)}`, [{ value: pct(p.s), label: `${p.k}건 / ${p.n}건` }]));
      });
      svgText(svg, 0, H - 4, tickLabel(pts[0].m, true));
      svgText(svg, W, H - 4, tickLabel(pts[n - 1].m, true), { "text-anchor": "end" });
      chart.appendChild(svg);
    }
  }
  function barList(id, rows) {
    const box = $(id); box.replaceChildren();
    const max = Math.max(...rows.map((r) => r.v));
    for (const r of rows) {
      const row = el("div", "bar-row"), track = el("div", "bar-track"), fill = el("div", "bar-fill");
      fill.style.width = (r.v / max) * 100 + "%"; track.appendChild(fill);
      row.append(el("span", "name", r.k), track, el("span", "v", fmt(r.v)));
      box.appendChild(row);
    }
  }
  function build() {
    built = true;
    $("r-volume-table").appendChild(table(["월", "보도자료"], RD.monthly_counts.map((d) => [monthLabel(d.m) + plabel(d.m), fmt(d.n)])));
    for (const { m, n } of RD.monthly_counts) {
      const row = el("div", "ledger-row"), left = el("div", "ledger-month"), chips = el("div", "chips");
      left.append(el("b", null, monthLabel(m)), el("span", "num", `${fmt(n)}건${m === PARTIAL ? ` · ${PNOTE}` : ""}`));
      if (m === GOV_M) row.classList.add("gov-row");
      (RD.distinctive[m] || []).slice(0, 6).forEach((t, i) => { const c = el("span", "chip" + (i === 0 ? " first" : ""), t.t); c.title = `${t.df}건에 등장`; chips.appendChild(c); });
      row.append(left, chips); $("r-ledger").appendChild(row);
    }
    for (const s of SHIFT) { const item = el("span"), k = el("span", "key"); k.style.borderTopColor = `var(${s.v})`; item.append(k, document.createTextNode(s.k)); $("r-shift-legend").appendChild(item); }
    $("r-shift-table").appendChild(table(["월", ...SHIFT.map((s) => s.k)], shiftData[0].pts.map((p, i) => [monthLabel(p.m), ...shiftData.map((s) => `${pct(s.pts[i].s)} (${s.pts[i].k}건)`)])));
    $("r-n-early").textContent = fmt(RD.pre_n); $("r-n-recent").textContent = fmt(RD.post_n);
    $("r-rising").appendChild(table(["단어", "출범 전", "출범 후"], RD.rising.slice(0, 12).map((r) => [r.term, fmt(r.ref_df), fmt(r.df)])));
    $("r-falling").appendChild(table(["단어", "출범 전", "출범 후"], RD.falling.slice(0, 12).map((r) => [r.term, fmt(r.df), fmt(r.ref_df)])));
    barList("r-terms", RD.top.map((r) => ({ k: r.term, v: r.df })));
    barList("r-depts", RD.departments.map((r) => ({ k: r.d, v: r.n })));
  }
  function draw() { volume(); shift(); topics(); }
  return { init() {}, show() { if (!built) build(); draw(); }, resize() { if (built) draw(); } };
})();

// =====================================================================
// 탭과 시작
// =====================================================================
const Tabs = (() => {
  const NAMES = ["ai", "rules", "search", "cloud", "network", "report"];
  const MODS = { ai: AI, rules: Rules, search: S, cloud: C, network: N, report: R };
  let current = null;
  function show(name, focusTab = false) {
    if (!NAMES.includes(name)) name = "ai";
    current = name;
    hideTip();
    for (const n of NAMES) {
      const on = n === name;
      $("tab-" + n).setAttribute("aria-selected", String(on));
      $("tab-" + n).tabIndex = on ? 0 : -1;
      $("panel-" + n).hidden = !on;
    }
    if (focusTab) $("tab-" + name).focus();
    store.set("moisdb.tab", name);
    try { if (location.hash !== "#" + name) history.replaceState(null, "", "#" + name); } catch {}
    MODS[name].show();
  }
  function init() {
    for (const n of NAMES) $("tab-" + n).addEventListener("click", () => show(n));
    document.querySelector(".tabs").addEventListener("keydown", (e) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      e.preventDefault();
      const i = NAMES.indexOf(current) + (e.key === "ArrowRight" ? 1 : -1);
      show(NAMES[(i + NAMES.length) % NAMES.length], true);
    });
    const fromHash = location.hash.replace("#", "");
    show(NAMES.includes(fromHash) ? fromHash : store.get("moisdb.tab") || "ai");
    let lastW = document.querySelector(".sheet").clientWidth, raf = 0;
    new ResizeObserver(() => {
      const w = document.querySelector(".sheet").clientWidth;
      if (Math.abs(w - lastW) < 12) return;
      lastW = w; cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => { hideTip(); MODS[current].resize(); });
    }).observe(document.querySelector(".sheet"));
    const themeChanged = () => { C.themeChanged(); if (current === "cloud") C.show(); };
    matchMedia("(prefers-color-scheme: dark)").addEventListener("change", themeChanged);
    new MutationObserver(themeChanged).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  }
  return { init, show };
})();

// ---- 보는 기간 단추 ----
const PeriodUi = (() => {
  function paint() {
    $("period-all").setAttribute("aria-pressed", String(!Period.gov));
    $("period-gov").setAttribute("aria-pressed", String(Period.gov));
  }
  function init() {
    $("period-all").addEventListener("click", () => Period.set(false));
    $("period-gov").addEventListener("click", () => Period.set(true));
    Period.onChange(() => {
      paint();
      applyPeriodToDocs();
      applyPeriodToCloud();
      S.rescope(); C.rescope(); N.rescope(); AI.rescope();
      if (DOCS.length) toast(`${Period.gov ? "이재명 정부 출범 이후" : "전체 기간"} 보도자료 ${fmt(DOCS.length)}건을 봅니다.`);
    });
    paint();
  }
  return { init };
})();

PeriodUi.init();
AI.init(); Rules.init(); S.init(); C.init(); N.init(); R.init();
Tabs.init();
})();
