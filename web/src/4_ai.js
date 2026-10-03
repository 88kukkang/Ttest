
// =====================================================================
// AI에게 묻기: sample 능력 + 페이지 안 검색 도구
// =====================================================================
const AI = (() => {
  const EXAMPLES = [
    "인구감소지역에 별도 혜택을 주는 것과 관련된 보도자료는?",
    "국가정보자원관리원 화재 이후 행안부가 내놓은 대책을 시간순으로 정리해줘",
    "고유가 피해지원금은 누가, 언제까지 받을 수 있어?",
    "‘지방정부’라는 표현은 언제부터 쓰기 시작했어?",
    "주민자치와 관련해 바뀐 제도가 있어?",
  ];
  const range = () => `${DOCS.reduce((a, d) => (d.date < a ? d.date : a), "9999")} ~ ${DOCS.reduce((a, d) => (d.date > a ? d.date : a), "")}`;
  const rules = () => `너는 행정안전부 보도자료 데이터베이스를 검색해 질문에 답하는 도우미다.

[데이터]
행정안전부 누리집 보도자료 게시판에 ${range()}에 등록된 보도자료 ${fmt(DOCS.length)}건. 본문은 첨부 원문(HWPX·PDF)에서 뽑은 텍스트다. 이 기간 밖의 일, 다른 부처 자료, 인터넷 정보는 이 데이터에 없다.
${Period.gov ? "사용자가 '이재명 정부 출범(2025. 6. 4.) 이후'만 보도록 골라 두었다. 도구도 이 기간 안에서만 찾는다." : "이재명 정부 출범일은 2025-06-04다. 그 전은 이전 정부 시기다. '이재명 정부 들어', '새 정부 이후' 같은 질문은 from을 2025-06-04로 좁혀 찾고, 정부별로 비교해 달라는 질문은 출범일 앞뒤로 나눠 찾아라."}

[도구]
- search_releases: 단어 일치 검색. all(모두 포함), any(하나 이상 포함), none(제외), from/to(YYYY-MM 또는 YYYY-MM-DD), dept(부서명 일부), sort(relevance|date), limit(최대 20). 한국어는 같은 뜻도 표현이 여러 가지라서, 핵심어는 all에 두고 비슷한 말은 any로 넓게 묶어라. 예) "인구감소지역 혜택" → all ["인구감소지역"], any ["특례","우대","감면","지원","가점","인센티브","혜택"]. 결과가 너무 많으면 all을 늘려 좁히고, 0건이면 말을 바꿔 다시 찾아라.
- read_release: id로 본문을 읽는다. 답의 근거는 반드시 실제로 읽은 본문에서 가져와라.
- count_by_month: 조건에 맞는 보도자료 수를 월별로 센다. '언제부터', '얼마나 자주', '추이' 질문에 쓴다.

[일하는 방식]
도구를 부를 수 있는 라운드는 몇 번뿐이다. 한 라운드에 여러 도구를 한꺼번에 불러라(검색 2~3개를 동시에, 그다음 유력한 본문 3~5개를 동시에). 도구를 쓰는 동안에는 설명을 쓰지 말고, 마지막에 답만 써라.

[답변 형식]
- 한국어. 먼저 질문에 대한 답을 2~4문장으로.
- 이어서 근거 보도자료를 날짜순 목록으로: "- 2025. 7. 10. [보도자료 제목](id:129005) — 한 줄 요지". 괄호 안에는 도구가 준 id를 "id:숫자"로 쓴다(인터넷 주소는 쓰지 않는다). 이 링크를 누르면 페이지 안에서 본문이 열린다.
- 숫자·금액·날짜·대상은 본문에 적힌 그대로 옮긴다. 추측하지 않는다.
- 찾지 못했으면 찾지 못했다고 말하고, 어떤 말로 찾아봤는지 적는다.
- 마크다운은 목록, 굵게(**), 링크만 쓴다. 표와 제목(#)은 쓰지 않는다.${Rules.promptBlock()}`;

  const ERR = {
    not_granted: ["이 페이지가 Claude를 쓰도록 허용되지 않았습니다. 페이지의 권한 메뉴에서 허용한 뒤 새로 고쳐 주세요.", true],
    sampling_disabled: ["이 계정이나 조직에서는 페이지에서 Claude를 쓸 수 없습니다. 검색 탭을 이용해 주세요.", true],
    not_declared: ["지금 화면에서는 이 기능을 쓸 수 없습니다.", true],
    capability_disabled: ["지금 화면에서는 이 기능을 쓸 수 없습니다.", true],
    capability_removed: ["지금 쓰는 Claude 앱에서는 이 기능을 쓸 수 없습니다. 앱이나 브라우저를 최신으로 바꿔 주세요.", true],
    rate_limited: ["요청이 많거나 사용량 한도에 닿았습니다. 잠시 뒤 다시 물어보세요.", false],
    session_expired: ["claude.ai에 다시 로그인한 뒤 물어보세요.", false],
    refused: ["Claude가 이 질문에는 답하지 않았습니다. 질문을 바꿔 보세요.", false],
    empty_completion: ["답이 비어 있습니다. 질문을 조금 더 구체적으로 바꿔 보세요.", false],
    prompt_too_large: ["대화가 길어졌습니다. ‘새 대화’를 누르고 다시 물어보세요.", false],
    invalid_json: ["검색 계획을 읽지 못했습니다. 다시 물어보세요.", false],
  };
  let samplePromise = null, toolsOK = false, turns = [], ctl = null, busy = false, disabled = false;

  function offMessage(text) {
    const box = $("ai-off");
    box.replaceChildren(el("b", null, "AI 질문을 쓸 수 없습니다"), el("span", null, text));
    box.hidden = false;
    disabled = true;
    $("ai-send").disabled = true;
    $("ai-q").disabled = true;
  }

  // ---- 안전한 마크다운(목록·굵게·링크만) → DOM ----
  /** 링크 대상에서 보도자료 번호를 꺼낸다: id:129005, #129005, 행안부 주소(nttId=…), 모델이 지어낸 "search id:129005" 같은 꼴까지 */
  function docIdOf(target) {
    const t = target.trim();
    if (/^https?:\/\//.test(t)) return t.startsWith("https://www.mois.go.kr/") ? (t.match(/[?&]nttId=(\d+)/) || [])[1] || null : null;
    const m = t.match(/^(?:[a-z ]*id\s*[:=]?\s*|#)?(\d{4,9})$/i);
    return m ? m[1] : null;
  }
  function inline(parent, s) {
    const re = /\[([^\]]+)\]\(([^)\n]{1,300})\)|\*\*([^*]+)\*\*/g;
    let last = 0, m;
    while ((m = re.exec(s))) {
      if (m.index > last) parent.appendChild(document.createTextNode(s.slice(last, m.index)));
      if (m[1]) {
        // 보도자료 링크는 읽기 창으로만 연다 (누리집으로 바로 넘어가지 않게)
        const id = docIdOf(m[2]);
        if (id) parent.appendChild(docButton(id, m[1]));
        else if (/^https?:\/\/\S+$/.test(m[2].trim())) { const a = el("a", null, m[1]); a.href = m[2].trim(); a.target = "_blank"; a.rel = "noopener"; parent.appendChild(a); }
        else parent.appendChild(document.createTextNode(m[1]));
      } else parent.appendChild(el("strong", null, m[3]));
      last = re.lastIndex;
    }
    if (last < s.length) parent.appendChild(document.createTextNode(s.slice(last)));
  }
  function renderMd(box, text) {
    const frag = document.createDocumentFragment();
    let list = null, type = null, para = [];
    const flush = () => { if (para.length) { const p = el("p"); inline(p, para.join(" ")); frag.appendChild(p); para = []; } };
    for (const raw of text.replace(/\r/g, "").split("\n")) {
      const line = raw.trimEnd();
      let m;
      if (!line.trim()) { flush(); list = null; type = null; continue; }
      if ((m = line.match(/^\s*#{1,6}\s+(.*)$/))) { flush(); list = null; type = null; const h = el("h4"); inline(h, m[1]); frag.appendChild(h); continue; }
      if ((m = line.match(/^\s*[-*•]\s+(.*)$/))) { flush(); if (type !== "ul") { list = el("ul"); type = "ul"; frag.appendChild(list); } const li = el("li"); inline(li, m[1]); list.appendChild(li); continue; }
      if ((m = line.match(/^\s*(\d+)[.)]\s+(.*)$/))) { flush(); if (type !== "ol") { list = el("ol"); type = "ol"; frag.appendChild(list); } const li = el("li"); inline(li, m[2]); list.appendChild(li); continue; }
      list = null; type = null; para.push(line.trim());
    }
    flush();
    box.replaceChildren(frag);
  }

  // ---- 도구 ----
  const strArr = (v) => (Array.isArray(v) ? v : v == null ? [] : [v]).map((x) => String(x).toLowerCase().trim()).filter(Boolean).slice(0, 12);
  const ym = (v) => (typeof v === "string" && /^\d{4}-\d{2}(-\d{2})?$/.test(v.trim()) ? v.trim() : "");
  const int = (v, dflt) => { const n = Math.floor(Number(v)); return Number.isFinite(n) ? n : dflt; };
  function describe(input) {
    const parts = [];
    const all = strArr(input.all), any = strArr(input.any), none = strArr(input.none);
    if (all.length) parts.push(all.join(" + "));
    if (any.length) parts.push(`(${any.join(" | ")})`);
    if (none.length) parts.push(none.map((t) => "-" + t).join(" "));
    if (ym(input.from) || ym(input.to)) parts.push(`${ym(input.from) || "처음"}~${ym(input.to) || "끝"}`);
    if (input.dept) parts.push(String(input.dept));
    return parts.join(" ");
  }
  function criteria(input) {
    const all = strArr(input.all), any = strArr(input.any), none = strArr(input.none);
    if (!all.length && !any.length) throw new Error("all 이나 any 에 검색어를 하나 이상 넣으세요.");
    return { all, any, none, from: ym(input.from), to: ym(input.to), deptLike: input.dept ? String(input.dept).trim() : "" };
  }
  const ARGS = {
    all: { type: "array", items: { type: "string" }, description: "모두 들어가야 하는 말" },
    any: { type: "array", items: { type: "string" }, description: "하나 이상 들어가야 하는 말(비슷한 말 묶음)" },
    none: { type: "array", items: { type: "string" }, description: "들어가면 안 되는 말" },
    from: { type: "string", description: "시작 월 YYYY-MM 또는 시작일 YYYY-MM-DD" },
    to: { type: "string", description: "끝 월 YYYY-MM 또는 끝 날 YYYY-MM-DD" },
    dept: { type: "string", description: "담당 부서 이름 일부 (예: 재난, 지방재정)" },
  };
  function makeTools(step, readMap) {
    return [
      {
        name: "search_releases",
        description: "행안부 보도자료를 단어 일치로 찾아 목록을 돌려준다. total=조건에 맞는 전체 건수, results=[{id, date, dept, title, hits(검색어 등장 횟수), snippet}]. 본문 내용은 read_release로 읽는다.",
        inputSchema: { type: "object", properties: { ...ARGS, sort: { type: "string", enum: ["relevance", "date"], description: "relevance(기본): 검색어가 많이 나온 순, date: 최신순" }, limit: { type: "integer", minimum: 1, maximum: 20, description: "돌려받을 건수 (기본 10)" } } },
        execute(input) {
          const c = criteria(input);
          const res = findDocs(c);
          if (input.sort === "date") res.sort((a, b) => (a.d.date < b.d.date ? 1 : -1));
          else res.sort((a, b) => b.score - a.score || (a.d.date < b.d.date ? 1 : -1));
          const limit = Math.min(20, Math.max(1, int(input.limit, 10)));
          step(`검색 ${describe(input)} → ${fmt(res.length)}건`);
          const terms = [...c.all, ...c.any];
          return { total: res.length, results: res.slice(0, limit).map((r) => ({ id: r.d.id, date: r.d.date, dept: r.d.dept, title: r.d.title, hits: r.hits, snippet: plainSnippet(r.d, terms) })) };
        },
      },
      {
        name: "read_release",
        description: "보도자료 하나의 본문을 읽는다. 긴 글은 앞에서부터 max_chars(기본 5000, 최대 8000)자만 온다. 더 읽으려면 offset을 늘린다.",
        inputSchema: { type: "object", properties: { id: { type: "string", description: "search_releases가 준 id" }, offset: { type: "integer", minimum: 0 }, max_chars: { type: "integer", minimum: 500, maximum: 8000 } }, required: ["id"] },
        execute(input) {
          const d = DOC_BY_ID.get(String(input.id).trim());
          if (!d) throw new Error(`id ${input.id} 인 보도자료가 없습니다.`);
          const off = Math.min(d.body.length, Math.max(0, int(input.offset, 0)));
          const n = Math.min(8000, Math.max(500, int(input.max_chars, 5000)));
          if (!readMap.has(d.id)) step(`읽음: ${dateLabel(d.date)} ${d.title}`);
          readMap.set(d.id, d);
          return { id: d.id, date: d.date, dept: d.dept, title: d.title, offset: off, total_chars: d.body.length, text: d.body.slice(off, off + n) };
        },
      },
      {
        name: "count_by_month",
        description: "조건에 맞는 보도자료 수를 월별로 센다. by_month={YYYY-MM: 건수}, month_totals={YYYY-MM: 그 달 전체 보도자료 수}.",
        inputSchema: { type: "object", properties: ARGS },
        execute(input) {
          const res = findDocs(criteria(input));
          const by = {}, totals = {};
          for (const m of MONTHS) { by[m] = 0; totals[m] = 0; }
          for (const d of DOCS) totals[d.month]++;
          for (const r of res) by[r.d.month]++;
          step(`월별 집계 ${describe(input)} → ${fmt(res.length)}건`);
          return { total: res.length, by_month: by, month_totals: totals, note: PARTIAL ? `${PARTIAL}은 ${PARTIAL_NOTE}만 있음` : "" };
        },
      },
    ];
  }

  // ---- 도구를 못 쓰는 화면: 검색 계획 → 페이지가 검색 → 자료를 붙여 한 번에 묻기 ----
  async function withoutTools(sample, q, history, signal, step, readMap, onText) {
    step("검색어 정하는 중");
    const plan = await sample.json(
      `행정안전부 보도자료(${range()})를 단어 일치로 검색해 다음 질문에 답하려 한다. 검색 계획을 JSON 하나로만 답하라.
형식: {"searches":[{"all":["핵심어"],"any":["비슷한 말", "..."]}]} (최대 3개, 비슷한 말은 any에 넓게)
질문: ${q}`,
      { modelTier: "quick", signal },
    );
    const merged = new Map();
    for (const s of (plan && Array.isArray(plan.searches) ? plan.searches : []).slice(0, 3)) {
      let c;
      try { c = criteria(s || {}); } catch { continue; }
      const res = findDocs(c);
      step(`검색 ${describe(s)} → ${fmt(res.length)}건`);
      for (const r of res) { const prev = merged.get(r.d.id); if (!prev || prev.score < r.score) merged.set(r.d.id, { ...r, terms: [...c.all, ...c.any] }); }
    }
    const top = [...merged.values()].sort((a, b) => b.score - a.score).slice(0, 8);
    if (!top.length) return "관련 보도자료를 찾지 못했습니다. 질문에 들어간 말을 바꿔서 다시 물어보세요.";
    const material = top.map((r) => {
      readMap.set(r.d.id, r.d);
      const wins = snippetWindows(r.d, r.terms, 3, 300).map(([s, e]) => r.d.body.slice(s, e).replace(/\s+/g, " ")).join(" … ");
      return `### ${dateLabel(r.d.date)} ${r.d.title}\nid: ${r.d.id}\n부서: ${r.d.dept}\n${r.d.body.slice(0, 600).replace(/\s+/g, " ")}\n…\n${wins}`;
    }).join("\n\n");
    step(`관련 보도자료 ${top.length}건으로 답하는 중`);
    const turnsNoTools = [{ role: "user", content: rules().replace(/\[도구\][\s\S]*?\[답변 형식\]/, "[답변 형식]") }, ...history.slice(0, -1),
      { role: "user", content: `질문: ${q}\n\n아래는 검색으로 찾은 보도자료 발췌다. 이 자료만 근거로 답하라.\n\n${material}` }];
    const { text } = await sample(turnsNoTools, { signal, onText, cache: false });
    return text;
  }

  // ---- 묻기 ----
  function trimmedHistory() {
    const keep = turns.slice(-7);
    while (keep.length && keep[0].role !== "user") keep.shift();
    return keep;
  }
  async function ask(q) {
    q = q.trim();
    if (!q || busy || disabled) return;
    const sample = await samplePromise;
    if (!sample) return;
    busy = true;
    $("ai-send").disabled = true; $("ai-stop").hidden = false; $("ai-new").hidden = false;
    const log = $("ai-log");
    const qEl = el("div", "ai-q", q);
    const aEl = el("div", "ai-a");
    const steps = el("ul", "ai-steps");
    const body = el("div", "ai-body");
    body.appendChild(el("p", "thinking", "생각하는 중…"));
    aEl.append(steps, body);
    log.append(qEl, aEl);
    qEl.scrollIntoView({ block: "nearest" });
    const step = (text) => { steps.querySelectorAll("li").forEach((li) => li.classList.add("done")); steps.appendChild(el("li", null, text)); };
    const readMap = new Map();
    let raf = 0, latest = "";
    const onText = ({ text }) => { latest = text; cancelAnimationFrame(raf); raf = requestAnimationFrame(() => renderMd(body, latest)); };
    turns.push({ role: "user", content: q });
    const history = trimmedHistory();
    ctl = new AbortController();
    try {
      await docsReady;
      let text, truncated = false;
      if (toolsOK) {
        try {
          const r = await sample([{ role: "user", content: rules() }, ...history], { signal: ctl.signal, tools: makeTools(step, readMap), onText });
          text = r.text; truncated = r.truncated;
        } catch (e) {
          if (e && e.code === "tools_unavailable") { toolsOK = false; text = await withoutTools(sample, q, history, ctl.signal, step, readMap, onText); }
          else throw e;
        }
      } else {
        text = await withoutTools(sample, q, history, ctl.signal, step, readMap, onText);
      }
      cancelAnimationFrame(raf);
      renderMd(body, text);
      steps.querySelectorAll("li").forEach((li) => li.classList.add("done"));
      if (truncated) body.appendChild(el("p", "ai-err", "답이 길어 중간에 끊겼습니다. 범위를 좁혀 다시 물어보세요."));
      turns.push({ role: "assistant", content: text });
      if (readMap.size) {
        const refs = el("div", "ai-refs");
        refs.appendChild(el("span", null, `Claude가 읽은 보도자료 ${readMap.size}건`));
        const ul = el("ul");
        for (const d of [...readMap.values()].sort((a, b) => (a.date < b.date ? -1 : 1))) {
          const li = el("li");
          li.append(`${dateLabel(d.date)} `, articleLink(d));
          ul.appendChild(li);
        }
        refs.appendChild(ul);
        aEl.appendChild(refs);
      }
    } catch (e) {
      cancelAnimationFrame(raf);
      turns.pop();
      const code = (e && e.code) || "upstream_error";
      if (e && e.text) renderMd(body, e.text); else body.replaceChildren();
      if (code === "cancelled") body.appendChild(el("p", "note", "멈췄습니다."));
      else {
        const [msg, permanent] = ERR[code] || ["연결이 끊겼습니다. 다시 물어보세요.", false];
        body.appendChild(el("p", "ai-err", msg));
        if (permanent) offMessage(msg);
      }
    } finally {
      busy = false;
      ctl = null;
      $("ai-stop").hidden = true;
      if (!disabled) $("ai-send").disabled = false;
    }
  }

  function init() {
    const exBox = $("ai-examples");
    for (const ex of EXAMPLES) {
      const b = el("button", "ex", ex); b.type = "button";
      b.addEventListener("click", () => { if (!busy) ask(ex); });
      exBox.appendChild(b);
    }
    $("ai-form").addEventListener("submit", (e) => { e.preventDefault(); const q = $("ai-q").value; if (q.trim() && !busy) { $("ai-q").value = ""; ask(q); } });
    $("ai-q").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); $("ai-form").requestSubmit(); } });
    $("ai-stop").addEventListener("click", () => ctl && ctl.abort());
    $("ai-new").addEventListener("click", () => { if (busy && ctl) ctl.abort(); turns = []; $("ai-log").replaceChildren(); $("ai-new").hidden = true; $("ai-q").focus(); });
    samplePromise = (window.claude && typeof window.claude.use === "function" ? window.claude.use("sample") : Promise.resolve(null))
      .catch(() => null)
      .then(async (s) => {
        if (!s) { offMessage("claude.ai에 로그인한 상태에서 이 페이지를 열어야 쓸 수 있습니다. 검색·키워드 클라우드·관계도는 그대로 쓸 수 있습니다."); return null; }
        const lim = await s.limits().catch(() => null);
        toolsOK = !!(lim && lim.tools);
        return s;
      });
  }
  /** 기간 보기를 바꾸면, 이어지는 질문부터 새 범위로 찾는다는 걸 대화에 남긴다 */
  function rescope() {
    if (!turns.length) return;
    $("ai-log").appendChild(el("p", "ai-mark", `여기부터는 ${Period.gov ? "이재명 정부 출범 이후" : "전체 기간"} 보도자료에서 찾습니다.`));
  }
  return { init, ask, rescope, show() {}, resize() {} };
})();
