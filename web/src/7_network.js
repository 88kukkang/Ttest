
// =====================================================================
// 관계도 탭
// =====================================================================
const N = (() => {
  const EXAMPLES = ["인공지능", "지방정부", "재난", "소비쿠폰", "국가정보자원관리원", "산불", "주민자치", "통합특별시"];
  const COMMON_SHARE = 0.5;
  let D = null, mode = "net", sel = [], graph = null, selected = null, zoom = null, svgSel = null, fitT = null, started = false, needsRender = false;

  function message(t) { const m = $("n-msg"); m.textContent = t || ""; m.hidden = !t; }
  function selection() {
    const from = $("n-from").value, to = $("n-to").value, dept = $("n-dept").value;
    sel = D.docs.filter((d) => (!from || d.month >= from) && (!to || d.month <= to) && (dept === "" || d.dept === +dept));
    const df = new Uint32Array(D.terms.length);
    for (const d of sel) for (const t of d.terms) df[t]++;
    return df;
  }
  const isCommon = (t, df) => $("n-common").checked && df[t] / Math.max(1, sel.length) >= COMMON_SHARE;
  function coMatrix(nodeTerms) {
    const n = nodeTerms.length, pos = new Int32Array(D.terms.length).fill(-1);
    nodeTerms.forEach((t, i) => (pos[t] = i));
    const co = new Uint32Array(n * n), present = [];
    for (const d of sel) {
      present.length = 0;
      for (const t of d.terms) if (pos[t] >= 0) present.push(pos[t]);
      for (let a = 0; a < present.length; a++) for (let b = a + 1; b < present.length; b++) { const i = present[a], j = present[b]; co[i * n + j]++; co[j * n + i]++; }
    }
    return co;
  }
  function knnEdges(nodes, co, df, k, skip = () => false) {
    const n = nodes.length, edges = new Map();
    for (let i = 0; i < n; i++) {
      if (skip(i)) continue;
      const cand = [];
      for (let j = 0; j < n; j++) {
        if (i === j || skip(j)) continue;
        const c = co[i * n + j];
        if (c >= 3) cand.push({ j, c, w: c / Math.sqrt(df[nodes[i].t] * df[nodes[j].t]) });
      }
      cand.sort((a, b) => b.w - a.w);
      for (const e of cand.slice(0, k)) {
        const key = i < e.j ? `${i}-${e.j}` : `${e.j}-${i}`;
        if (!edges.has(key)) edges.set(key, { source: Math.min(i, e.j), target: Math.max(i, e.j), co: e.c, w: e.w });
      }
    }
    return [...edges.values()];
  }
  // 루뱅 1단계(국소 이동)
  function communities(n, edges, skip) {
    const adj = Array.from({ length: n }, () => []);
    let m2 = 0;
    for (const e of edges) { adj[e.source].push([e.target, e.w]); adj[e.target].push([e.source, e.w]); m2 += 2 * e.w; }
    const k = adj.map((a) => a.reduce((s, x) => s + x[1], 0));
    const comm = Array.from({ length: n }, (_, i) => i), tot = k.slice();
    if (!m2) return comm;
    for (let pass = 0; pass < 20; pass++) {
      let moved = false;
      for (let i = 0; i < n; i++) {
        if (skip(i) || !adj[i].length) continue;
        const ci = comm[i];
        tot[ci] -= k[i];
        const links = new Map();
        for (const [j, w] of adj[i]) if (!skip(j)) links.set(comm[j], (links.get(comm[j]) || 0) + w);
        let best = ci, bestGain = (links.get(ci) || 0) - (tot[ci] * k[i]) / m2;
        for (const [c, w] of links) { const g = w - (tot[c] * k[i]) / m2; if (g > bestGain + 1e-12 || (Math.abs(g - bestGain) <= 1e-12 && c < best)) { best = c; bestGain = g; } }
        comm[i] = best; tot[best] += k[i];
        if (best !== ci) moved = true;
      }
      if (!moved) break;
    }
    return comm;
  }
  function buildNet(df) {
    const cand = [];
    for (let t = 0; t < df.length; t++) if (df[t] >= 3 && !isCommon(t, df)) cand.push(t);
    cand.sort((a, b) => df[b] - df[a] || a - b);
    const nodes = cand.slice(0, +$("n-n").value).map((t) => ({ t, term: D.terms[t], df: df[t] }));
    const co = coMatrix(nodes.map((x) => x.t));
    return { nodes, links: knnEdges(nodes, co, df, +$("n-k").value), co, center: -1 };
  }
  function findTerm(q) {
    q = q.trim();
    if (!q) return { t: -1 };
    const exact = D.termIndex.get(q);
    if (exact != null) return { t: exact };
    let best = -1;
    for (let t = 0; t < D.terms.length; t++) if (D.terms[t].includes(q) && (best < 0 || D.totalDf[t] > D.totalDf[best])) best = t;
    return { t: best, approx: best >= 0 };
  }
  function buildEgo(df) {
    const q = $("n-center").value;
    const { t: c, approx } = findTerm(q);
    if (c < 0) { message(`‘${q.trim()}’이(가) 들어간 단어를 찾지 못했습니다. 다른 말로 해 보세요.`); return null; }
    if (approx) message(`‘${q.trim()}’ 단어가 따로 없어 가장 많이 나온 ‘${D.terms[c]}’로 보여줍니다.`);
    const withC = sel.filter((d) => d.termSet.has(c)), nc = withC.length;
    if (nc < 3) { message(`고른 범위에서 ‘${D.terms[c]}’이(가) 나온 보도자료가 ${nc}건뿐이라 연관어를 고를 수 없습니다. 기간이나 부서를 넓혀 보세요.`); return null; }
    const dfc = new Uint32Array(D.terms.length);
    for (const d of withC) for (const t of d.terms) dfc[t]++;
    const N = Math.max(10, Math.round(+$("n-n").value * 0.6)), n = sel.length, cand = [];
    for (let t = 0; t < df.length; t++) {
      if (t === c || dfc[t] < 3 || isCommon(t, df)) continue;
      if (D.terms[c].includes(D.terms[t])) continue; // 중심어의 조각(인공지능 → 인공, 지능)은 연관어가 아니다
      const lift = (dfc[t] / nc) / (df[t] / n);
      if (lift <= 1) continue;
      cand.push({ t, co: dfc[t], score: dfc[t] * Math.log1p(lift) });
    }
    cand.sort((a, b) => b.score - a.score || a.t - b.t);
    const rel = cand.slice(0, N);
    const nodes = [{ t: c, term: D.terms[c], df: df[c], center: true }, ...rel.map((r) => ({ t: r.t, term: D.terms[r.t], df: df[r.t] }))];
    const co = coMatrix(nodes.map((x) => x.t));
    const maxScore = rel.length ? rel[0].score : 1;
    const spokes = rel.map((r, i) => ({ source: 0, target: i + 1, co: r.co, w: r.co / Math.sqrt(df[c] * df[r.t]), spoke: true, s: r.score / maxScore }));
    const among = knnEdges(nodes, co, df, Math.min(2, +$("n-k").value), (i) => i === 0);
    return { nodes, links: [...spokes, ...among], co, center: 0, nc };
  }
  function render() {
    if (!D) return;
    hideTip(); message("");
    const df = selection();
    graph = mode === "net" ? buildNet(df) : buildEgo(df);
    const stage = $("n-stage");
    if (!graph || !graph.nodes.length) { stage.replaceChildren(); $("n-legend").replaceChildren(); $("n-table").replaceChildren(); $("n-meta").textContent = `보도자료 ${fmt(sel.length)}건`; return; }
    const { nodes, links } = graph;
    const skip = (i) => i === graph.center;
    const comm = communities(nodes.length, links.filter((l) => !l.spoke), skip);
    const groups = new Map();
    nodes.forEach((nd, i) => { if (skip(i)) return; if (!groups.has(comm[i])) groups.set(comm[i], []); groups.get(comm[i]).push(i); });
    const ranked = [...groups.values()].filter((g) => g.length >= 2).sort((a, b) => b.reduce((s, i) => s + nodes[i].df, 0) - a.reduce((s, i) => s + nodes[i].df, 0));
    nodes.forEach((nd) => (nd.group = -1));
    ranked.slice(0, 6).forEach((g, gi) => g.forEach((i) => (nodes[i].group = gi)));
    const color = (nd) => (nd.center ? "var(--center)" : nd.group >= 0 ? `var(--c${nd.group + 1})` : "var(--other)");

    const W = Math.max(300, stage.clientWidth), H = Math.round(Math.max(420, Math.min(700, W * 0.68)));
    const maxDf = d3.max(nodes, (d) => d.df), minDf = d3.min(nodes, (d) => d.df);
    const rScale = d3.scaleSqrt().domain([minDf, maxDf]).range([5, mode === "ego" ? 18 : 20]);
    const fScale = d3.scaleSqrt().domain([minDf, maxDf]).range([11, 16]);
    nodes.forEach((d) => { d.r = d.center ? 24 : rScale(d.df); d.fs = d.center ? 18 : fScale(d.df); });
    const sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).distance((l) => (l.spoke ? 70 + 150 * (1 - l.s) : 40 + 110 * (1 - Math.min(1, l.w * 2)))).strength((l) => (l.spoke ? 0.25 : 0.15 + 0.6 * Math.min(1, l.w * 2))))
      .force("charge", d3.forceManyBody().strength(mode === "ego" ? -260 : -200))
      .force("collide", d3.forceCollide((d) => d.r + d.fs * d.term.length * 0.32 + 4).iterations(2))
      .force("x", d3.forceX(W / 2).strength(0.04)).force("y", d3.forceY(H / 2).strength(0.06))
      .stop();
    if (graph.center >= 0) { nodes[0].fx = W / 2; nodes[0].fy = H / 2; }
    for (let i = 0; i < 400; i++) sim.tick();

    const svg = d3.create("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("height", H).attr("role", "img").attr("aria-label", mode === "net" ? "키워드 관계망" : `${nodes[0].term} 연관어 관계도`);
    const g = svg.append("g");
    const wMax = d3.max(links, (l) => l.w) || 1;
    const linkG = g.append("g");
    const linkSel = linkG.selectAll("line.link").data(links).join("line").attr("class", "link")
      .attr("stroke-width", (l) => (l.spoke ? 1 + 4 * l.s : 1 + 4 * (l.w / wMax)))
      .attr("stroke-opacity", (l) => (l.spoke ? 0.35 + 0.5 * l.s : 0.3 + 0.55 * (l.w / wMax))).attr("stroke-linecap", "round");
    const hitSel = linkG.selectAll("line.link-hit").data(links).join("line").attr("class", "link-hit");
    const nodeSel = g.append("g").selectAll("g.node").data(nodes).join("g").attr("class", "node").attr("tabindex", 0).attr("role", "button").attr("aria-label", (d) => `${d.term}, 보도자료 ${d.df}건`);
    nodeSel.append("circle").attr("r", (d) => d.r).style("fill", color);
    nodeSel.append("text").text((d) => d.term).attr("font-size", (d) => d.fs).attr("font-weight", (d) => (d.center || d.r > 12 ? 700 : 500))
      .attr("x", (d) => (d.center ? 0 : d.r + 4)).attr("y", (d) => (d.center ? d.r + d.fs + 2 : 0)).attr("dy", (d) => (d.center ? 0 : "0.35em")).attr("text-anchor", (d) => (d.center ? "middle" : "start"));
    const place = () => {
      for (const s of [linkSel, hitSel]) s.attr("x1", (l) => l.source.x).attr("y1", (l) => l.source.y).attr("x2", (l) => l.target.x).attr("y2", (l) => l.target.y);
      nodeSel.attr("transform", (d) => `translate(${d.x},${d.y})`);
    };
    place();
    const nb = new Map(nodes.map((d) => [d, new Set([d])]));
    for (const l of links) { nb.get(l.source).add(l.target); nb.get(l.target).add(l.source); }
    const focus = (d) => {
      if (!d) { nodeSel.classed("dim", false); linkSel.classed("dim", false).classed("hl", false); return; }
      const s = nb.get(d);
      nodeSel.classed("dim", (x) => !s.has(x));
      linkSel.classed("dim", (l) => l.source !== d && l.target !== d).classed("hl", (l) => l.source === d || l.target === d);
    };
    const nodeTip = (e, d) => showTip(d.term, `보도자료 ${fmt(d.df)}건 · 연결 ${nb.get(d).size - 1}개`, e.clientX, e.clientY);
    nodeSel.on("pointerenter", (e, d) => { focus(d); nodeTip(e, d); }).on("pointermove", nodeTip)
      .on("pointerleave", () => { focus(null); hideTip(); })
      .on("click", (e, d) => { if (!e.defaultPrevented) selectNode(d); })
      .on("keydown", (e, d) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectNode(d); } })
      .on("focus", (e, d) => { focus(d); const r = e.currentTarget.getBoundingClientRect(); showTip(d.term, `보도자료 ${fmt(d.df)}건`, r.left + r.width / 2, r.top); })
      .on("blur", () => { focus(null); hideTip(); });
    hitSel.on("pointermove", (e, l) => showTip(`${l.source.term} + ${l.target.term}`, `함께 나온 보도자료 ${fmt(l.co)}건`, e.clientX, e.clientY))
      .on("pointerenter", (e, l) => linkSel.filter((x) => x === l).classed("hl", true))
      .on("pointerleave", (e, l) => { linkSel.filter((x) => x === l).classed("hl", false); hideTip(); })
      .on("click", (e, l) => selectEdge(l));
    nodeSel.call(d3.drag()
      .on("start", (e, d) => { if (!e.active) sim.alphaTarget(0.15).restart(); d.fx = d.x; d.fy = d.y; hideTip(); })
      .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
      .on("end", (e, d) => { if (!e.active) sim.alphaTarget(0); if (!d.center) { d.fx = null; d.fy = null; } }));
    sim.on("tick", place);
    zoom = d3.zoom().scaleExtent([0.4, 4]).on("zoom", (e) => g.attr("transform", e.transform));
    svg.call(zoom).on("dblclick.zoom", null);
    const xs = nodes.map((d) => d.x), ys = nodes.map((d) => d.y);
    const x0 = d3.min(xs) - 30, x1 = d3.max(xs) + 120, y0 = d3.min(ys) - 30, y1 = d3.max(ys) + 30;
    const k = Math.min(1.4, W / (x1 - x0), H / (y1 - y0));
    fitT = d3.zoomIdentity.translate(W / 2 - (k * (x0 + x1)) / 2, H / 2 - (k * (y0 + y1)) / 2).scale(k);
    svg.call(zoom.transform, fitT);
    svgSel = svg;
    stage.replaceChildren(svg.node());

    const lg = $("n-legend"); lg.replaceChildren();
    const legendItem = (bg, text) => { const s = el("span"); const sw = el("span", "sw"); sw.style.background = bg; s.append(sw, text); lg.appendChild(s); };
    if (graph.center >= 0) legendItem("var(--center)", `중심어 ${nodes[0].term}`);
    ranked.slice(0, 6).forEach((grp, gi) => legendItem(`var(--c${gi + 1})`, `묶음 ${gi + 1} · ${grp.slice().sort((a, b) => nodes[b].df - nodes[a].df).slice(0, 4).map((i) => nodes[i].term).join(" · ")}`));
    if (nodes.some((d) => d.group < 0 && !d.center)) legendItem("var(--other)", "어느 묶음에도 속하지 않음");
    $("n-title").textContent = mode === "net" ? "전체 관계망" : `‘${nodes[0].term}’ 연관어`;
    const range = [$("n-from").value ? monthLabel($("n-from").value) : "처음", $("n-to").value ? monthLabel($("n-to").value) : "끝"].join(" ~ ");
    $("n-meta").textContent = `보도자료 ${fmt(sel.length)}건${graph.nc ? ` 중 중심어 포함 ${fmt(graph.nc)}건` : ""} · 단어 ${nodes.length}개 · 연결 ${links.length}개 · ${range}${$("n-dept").value !== "" ? " · " + D.depts[+$("n-dept").value] : ""}`;
    $("n-table").replaceChildren(table(["단어 A", "단어 B", "함께 나온 보도자료", "연결 강도(코사인)"],
      links.slice().sort((a, b) => b.co - a.co).map((l) => [l.source.term, l.target.term, fmt(l.co), l.w.toFixed(3)]), "data left2"));
    const keep = selected && selected.type === "node" && nodes.find((d) => d.term === selected.term);
    selectNode(keep || (graph.center >= 0 ? nodes[0] : nodes.reduce((a, b) => (b.df > a.df ? b : a))));
  }
  function docList(filterFn, title, terms = []) {
    const list = sel.filter(filterFn);
    $("n-docs-title").textContent = `${title} (${fmt(list.length)}건 중 최근 ${Math.min(6, list.length)}건)`;
    const ul = $("n-docs"); ul.replaceChildren();
    for (const d of list.slice(0, 6)) { const li = el("li"); li.append(el("span", "d-meta num", `${dateLabel(d.date)} · ${D.depts[d.dept] || "부서 미상"}`), articleLink(d, terms)); ul.appendChild(li); }
  }
  function selectNode(d) {
    selected = { type: "node", term: d.term };
    if (svgSel) svgSel.selectAll("g.node").classed("sel", (x) => x === d);
    $("n-sel-label").textContent = d.center ? "중심어" : "고른 단어";
    $("n-sel-name").textContent = d.term;
    $("n-sel-figs").textContent = `고른 범위 보도자료 ${fmt(sel.length)}건 중 ${fmt(d.df)}건`;
    const act = $("n-sel-actions"); act.replaceChildren();
    if (!d.center) { const b = el("button", "btn-ghost", "이 단어를 중심으로 보기"); b.type = "button"; b.addEventListener("click", () => center(d.term)); act.appendChild(b); }
    const s = el("button", "btn-ghost", "이 단어로 검색"); s.type = "button"; s.addEventListener("click", () => { S.query(d.term); Tabs.show("search"); }); act.appendChild(s);
    const i = graph.nodes.indexOf(d), n = graph.nodes.length;
    const rows = graph.nodes.map((x, j) => ({ x, c: j === i ? 0 : graph.co[i * n + j] })).filter((r) => r.c > 0).sort((a, b) => b.c - a.c).slice(0, 8);
    const bars = $("n-sel-bars"); bars.replaceChildren();
    if (rows.length) bars.appendChild(el("span", "note", "그린 단어 가운데 함께 많이 나온 말"));
    const max = rows.length ? rows[0].c : 1;
    for (const r of rows) {
      const row = el("div", "bar-row");
      const nameBtn = el("button", "name", r.x.term); nameBtn.type = "button"; nameBtn.addEventListener("click", () => selectNode(r.x));
      const track = el("div", "bar-track"), fill = el("div", "bar-fill"); fill.style.width = (r.c / max) * 100 + "%"; track.appendChild(fill);
      row.append(nameBtn, track, el("span", "v", fmt(r.c)));
      bars.appendChild(row);
    }
    docList((doc) => doc.termSet.has(d.t), `‘${d.term}’이(가) 나온 보도자료`, [d.term.toLowerCase()]);
  }
  function selectEdge(l) {
    selected = { type: "edge" };
    if (svgSel) svgSel.selectAll("g.node").classed("sel", (x) => x === l.source || x === l.target);
    $("n-sel-label").textContent = "고른 연결";
    $("n-sel-name").textContent = `${l.source.term} + ${l.target.term}`;
    $("n-sel-figs").textContent = `함께 나온 보도자료 ${fmt(l.co)}건 · 연결 강도 ${l.w.toFixed(3)}`;
    $("n-sel-actions").replaceChildren(); $("n-sel-bars").replaceChildren();
    docList((doc) => doc.termSet.has(l.source.t) && doc.termSet.has(l.target.t), "두 단어가 함께 나온 보도자료", [l.source.term.toLowerCase(), l.target.term.toLowerCase()]);
  }
  function setMode(m) { setModeUi(m); render(); }
  function setModeUi(m) {
    mode = m;
    $("n-mode-net").setAttribute("aria-pressed", String(m === "net"));
    $("n-mode-ego").setAttribute("aria-pressed", String(m === "ego"));
    $("n-centerbox").hidden = m !== "ego";
    selected = null;
  }
  /** 다른 탭에서 '관계도에서 보기': 탭이 보일 때 그린다 (숨은 채로 그리면 크기를 못 잰다) */
  function center(term) {
    $("n-center").value = term;
    setModeUi("ego");
    if (D && !$("panel-network").hidden) render(); else needsRender = true;
  }
  async function start() {
    started = true;
    if (!window.d3) { $("n-meta").textContent = "그래프 라이브러리(d3)를 불러오지 못했습니다. 페이지를 새로 고쳐 보세요."; return; }
    try { D = await cloudReady(); } catch (e) { $("n-meta").textContent = `불러오지 못했습니다 (${e.message}).`; return; }
    fillCloudFilters("n", D);
    const dl = $("n-terms");
    [...D.totalDf.keys()].sort((a, b) => D.totalDf[b] - D.totalDf[a]).slice(0, 1500).forEach((t) => dl.appendChild(new Option(D.terms[t])));
    if (window.innerWidth < 520) $("n-n").value = "30";
    needsRender = false;
    render();
  }
  function init() {
    $("n-mode-net").addEventListener("click", () => setMode("net"));
    $("n-mode-ego").addEventListener("click", () => setMode("ego"));
    $("n-centerbox").addEventListener("submit", (e) => { e.preventDefault(); selected = null; render(); });
    for (const ex of EXAMPLES) { const b = el("button", "ex", ex); b.type = "button"; b.addEventListener("click", () => { $("n-center").value = ex; selected = null; render(); }); $("n-centerbox").appendChild(b); }
    for (const id of ["n-from", "n-to", "n-dept", "n-n", "n-k", "n-common"]) $(id).addEventListener("change", render);
    $("n-reset").addEventListener("click", () => { if (svgSel && fitT) svgSel.transition().duration(300).call(zoom.transform, fitT); });
  }
  return { init, show() { if (!started) start(); else if (needsRender) { needsRender = false; render(); } }, resize() { render(); }, center };
})();
