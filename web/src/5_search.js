
// =====================================================================
// 검색 탭
// =====================================================================
const S = (() => {
  const PAGE = 30;
  const EXAMPLES = ["지방정부", "소비쿠폰", "\"국가정보자원관리원 화재\"", "인공지능", "통합특별시", "고유가 피해지원금", "산불 -훈련"];
  let ready = false, shown = PAGE, last = null, monthOnly = null, timer = 0;

  function run() {
    if (!ready) return;
    const q = $("s-q").value;
    store.set("moisdb.q", q);
    const { terms, excludes } = parseQuery(q);
    const scope = $("s-scope").value;
    const base = findDocs({ all: terms, none: excludes, dept: $("s-dept").value, scope });
    const byMonth = new Map(MONTHS.map((m) => [m, 0]));
    for (const r of base) byMonth.set(r.d.month, byMonth.get(r.d.month) + 1);
    const from = $("s-from").value, to = $("s-to").value;
    const inRange = (m) => (monthOnly ? m === monthOnly : (!from || m >= from) && (!to || m <= to));
    const list = base.filter((r) => inRange(r.d.month));
    if ($("s-sort").value === "score" && terms.length) list.sort((a, b) => b.score - a.score || (a.d.date < b.d.date ? 1 : -1));
    last = { list, terms, q: q.trim(), byMonth, inRange };
    shown = PAGE;
    summary(); hist(); renderList();
  }
  function summary() {
    const { list, q } = last;
    $("s-count").textContent = fmt(list.length) + "건";
    const parts = [q ? `‘${q}’ 검색 결과` : "전체 보도자료"];
    if ($("s-dept").value) parts.push($("s-dept").value);
    if (monthOnly) parts.push(monthLabel(monthOnly) + "만");
    $("s-count-sub").textContent = parts.join(" · ") + ` (전체 ${fmt(DOCS.length)}건 중)`;
    $("s-copy").disabled = !list.length;
    const label = $("s-hist-label");
    label.replaceChildren(document.createTextNode("월별 건수 · 막대를 누르면 그 달만 봅니다"));
    if (monthOnly) {
      const chip = el("span", "active-month", `${monthLabel(monthOnly)}만 보는 중`);
      const x = el("button", null, "해제"); x.type = "button"; x.addEventListener("click", () => { monthOnly = null; run(); });
      chip.appendChild(x); label.append(" ", chip);
    }
  }
  function hist() {
    const box = $("s-hist");
    if (!last || box.clientWidth === 0) return;
    const { byMonth, inRange } = last;
    const W = Math.max(280, box.clientWidth), H = 120, m = { l: 30, r: 6, t: 18, b: 22 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b, n = MONTHS.length;
    const vals = MONTHS.map((mm) => byMonth.get(mm) || 0);
    const raw = Math.max(1, ...vals);
    let tick = raw <= 5 ? 1 : raw <= 20 ? 5 : raw <= 50 ? 10 : raw <= 100 ? 25 : 50;
    while (Math.ceil(raw / tick) > 3) tick *= 2;
    const yMax = Math.ceil(raw / tick) * tick;
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": "검색 결과 월별 건수" });
    for (let v = 0; v <= yMax; v += tick) {
      const y = m.t + ih - (v / yMax) * ih;
      svgEl("line", { x1: m.l, x2: W - m.r, y1: y, y2: y, class: v === 0 ? "base" : "grid" }, svg);
      svgText(svg, m.l - 6, y + 4, String(v), { "text-anchor": "end", class: "num" });
    }
    const band = iw / n, bw = Math.min(24, band * 0.62), step = band < 30 ? 2 : 1, maxI = vals.indexOf(Math.max(...vals));
    const totals = new Map(MONTHS.map((mm) => [mm, 0]));
    for (const d of DOCS) totals.set(d.month, totals.get(d.month) + 1);
    MONTHS.forEach((mm, i) => {
      const cx = m.l + band * i + band / 2, h = (vals[i] / yMax) * ih, y = m.t + ih - h;
      const hit = svgEl("rect", { x: m.l + band * i, y: 0, width: band, height: m.t + ih, class: "hit click", tabindex: 0, role: "button", "aria-label": `${monthLabel(mm)} ${vals[i]}건, 이 달만 보기` }, svg);
      svgEl("path", { d: colPath(cx - bw / 2, y, bw, h, 4), class: "mark", style: `fill:var(${inRange(mm) ? "--bar" : "--bar-dim"})` }, svg);
      bindHover(hit, () => fillTip(monthLabel(mm) + partialLabel(mm), [{ value: `${fmt(vals[i])}건`, label: `/ 그 달 ${fmt(totals.get(mm))}건` }]));
      const pick = () => { monthOnly = monthOnly === mm ? null : mm; hideTip(); run(); };
      hit.addEventListener("click", pick);
      hit.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
      if (i % step === 0) svgText(svg, cx, H - 6, tickLabel(mm, i === 0), { "text-anchor": "middle" });
      if (i === maxI && vals[i] > 0) svgText(svg, cx, y - 5, String(vals[i]), { "text-anchor": "middle", class: "val num" });
    });
    box.replaceChildren(svg);
  }
  function renderList() {
    const box = $("s-results");
    box.replaceChildren();
    const { list, terms } = last;
    if (!list.length) { box.appendChild(el("p", "empty", "찾는 글이 없습니다. 검색어를 줄이거나 기간·부서 조건을 넓혀 보세요. 문장으로 묻고 싶다면 ‘AI에게 묻기’ 탭을 써 보세요.")); return; }
    for (const r of list.slice(0, shown)) box.appendChild(item(r, terms));
    if (list.length > shown) {
      const row = el("div", "more-row");
      const more = el("button", "btn-ghost", `더 보기 (${fmt(Math.min(PAGE, list.length - shown))}건 더 · 남은 ${fmt(list.length - shown)}건)`);
      more.type = "button";
      more.addEventListener("click", () => { shown += PAGE; renderList(); });
      row.appendChild(more); box.appendChild(row);
    }
  }
  function item(r, terms) {
    const { d } = r;
    const art = el("article", "item");
    const meta = el("div", "item-meta");
    meta.append(el("span", "num", dateLabel(d.date)), el("span", null, d.dept || "부서 미상"));
    if (terms.length) meta.appendChild(el("span", "count num", `검색어 ${fmt(r.hits)}회`));
    const h = el("h4");
    h.appendChild(articleLink(d, terms, terms.length ? highlighted(d.title, d.lt, terms) : null));
    art.append(meta, h);
    const sn = el("div", "snips");
    if (terms.length) {
      const flat = d.body.replace(/\n/g, " "), flatLower = d.lb.replace(/\n/g, " ");
      for (const [s, e] of snippetWindows(d, terms)) {
        const p = el("p");
        if (s > 0) p.appendChild(document.createTextNode("… "));
        p.appendChild(highlighted(flat, flatLower, terms, s, e));
        if (e < d.body.length) p.appendChild(document.createTextNode(" …"));
        sn.appendChild(p);
      }
    } else sn.appendChild(el("p", null, d.body.slice(0, 140).replace(/\n/g, " ") + (d.body.length > 140 ? " …" : "")));
    if (sn.childNodes.length) art.appendChild(sn);
    const actions = el("div", "item-actions");
    const btn = el("button", "btn-ghost", "본문 펼치기"); btn.type = "button"; btn.setAttribute("aria-expanded", "false");
    const full = el("div", "full"); full.hidden = true;
    btn.addEventListener("click", () => {
      const open = full.hidden;
      if (open && !full.childNodes.length) full.appendChild(terms.length ? highlighted(d.body, d.lb, terms) : document.createTextNode(d.body));
      full.hidden = !open; btn.textContent = open ? "본문 접기" : "본문 펼치기"; btn.setAttribute("aria-expanded", String(open));
    });
    actions.append(btn);
    art.append(actions, full);
    return art;
  }
  /** 기간·부서 선택 상자를 지금 기간의 자료로 채운다 (고른 부서는 남아 있으면 유지) */
  function fill() {
    fillMonthSelects("s-from", "s-to", MONTHS);
    const dsel = $("s-dept"), prev = dsel.value;
    dsel.length = 1;
    dsel.options[0].textContent = `전체 부서 (${DEPT_COUNTS.length})`;
    for (const [name, n] of DEPT_COUNTS) dsel.appendChild(new Option(`${name || "부서 미상"} (${n})`, name));
    if (prev && DEPT_COUNTS.some(([name]) => name === prev)) dsel.value = prev;
  }
  function rescope() { if (!ready) return; fill(); monthOnly = null; run(); }
  function init() {
    const exBox = $("s-examples");
    for (const ex of EXAMPLES) {
      const b = el("button", "ex", ex); b.type = "button";
      b.addEventListener("click", () => { $("s-q").value = ex; monthOnly = null; run(); });
      exBox.appendChild(b);
    }
    $("s-form").addEventListener("submit", (e) => { e.preventDefault(); clearTimeout(timer); monthOnly = null; run(); });
    $("s-q").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { monthOnly = null; run(); }, 250); });
    for (const id of ["s-from", "s-to", "s-dept", "s-scope", "s-sort"]) $(id).addEventListener("change", () => { if (id === "s-from" || id === "s-to") monthOnly = null; run(); });
    $("s-copy").addEventListener("click", () => {
      const rows = [["등록일", "부서", "제목", "검색어 횟수", "원문 주소"]].concat(last.list.map((r) => [r.d.date, r.d.dept, r.d.title, r.hits, ARTICLE + r.d.id]));
      navigator.clipboard.writeText(rows.map((r) => r.join("\t")).join("\n"))
        .then(() => toast(`${fmt(last.list.length)}건을 복사했습니다. 엑셀에 붙여넣으면 됩니다.`), () => toast("이 화면에서는 복사가 막혀 있습니다."));
    });
    docsReady.then(() => {
      fill();
      const saved = store.get("moisdb.q");
      if (!$("s-q").value) $("s-q").value = saved != null ? saved : "지방정부";
      ready = true;
      run();
    }).catch((e) => { $("s-count").textContent = ""; $("s-count-sub").textContent = ""; $("s-results").replaceChildren(el("p", "empty", `보도자료 데이터를 불러오지 못했습니다 (${e.message}). 페이지를 새로 고쳐 보세요.`)); });
  }
  /** 다른 탭에서 '이 단어로 검색' */
  function query(q) { $("s-q").value = q; monthOnly = null; ["s-from", "s-to", "s-dept"].forEach((id) => ($(id).value = "")); run(); }
  return { init, show() { hist(); }, resize() { hist(); }, query, rescope };
})();
