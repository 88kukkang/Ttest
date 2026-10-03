// =====================================================================
// AI 규칙: 이 페이지를 쓰는 사람들이 함께 고치는 규칙 (db 능력).
// 켜 둔 규칙은 'AI에게 묻기' 지시문 끝에 [팀 규칙]으로 붙는다.
//   rules/{id}     {kind: term|style, title, body, example, enabled, order, createdBy, createdAt, updatedBy, updatedAt}
//   rules_log/{id} {ruleId, action, title, before, after, by, at}   ← 되돌리기용 변경 기록
// =====================================================================
const Rules = (() => {
  const BUDGET = 4000; // AI에 전달하는 규칙 전체 글자 수 한도 (질문마다 함께 보내므로 사용량에 들어감)
  const KIND = { term: "용어 기준", style: "답변 방식" };
  const ACTION = { create: "추가", update: "수정", delete: "삭제", on: "켬", off: "끔", restore: "되돌림" };
  const CLAUDE_ID = "claude"; // Claude가 대신 적은 항목(예시 규칙)
  let db = null, user = null, myId = null;
  let writable = null; // true/false = 플랫폼이 알려준 값, null = 알려주지 않음 → 써 보고 판단
  let rules = [], log = [], loaded = false, editing = null, deleteArm = null, renderSeq = 0;

  const str = (v, max) => String(v == null ? "" : v).slice(0, max);
  const normalize = (id, d) => ({
    id, kind: d.kind === "style" ? "style" : "term", title: str(d.title, 40), body: str(d.body, 1000), example: str(d.example, 200),
    enabled: d.enabled !== false, order: Number(d.order) || 0,
    createdBy: d.createdBy || null, createdAt: str(d.createdAt, 40), updatedBy: d.updatedBy || null, updatedAt: str(d.updatedAt, 40),
  });
  const bodyOf = (r) => { const { id, ...rest } = r; return rest; };
  const when = (iso) => {
    const d = new Date(iso);
    if (!iso || isNaN(d)) return "";
    return `${d.getFullYear()}. ${d.getMonth() + 1}. ${d.getDate()}. ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  };
  const oneLine = (s) => String(s || "").replace(/\s*\n\s*/g, " / ").trim();
  const lineOf = (r) => `- [${r.kind === "style" ? "답변" : "용어"}] ${oneLine(r.title)}: ${oneLine(r.body)}`;
  const sorted = () => [...rules].sort((a, b) => (a.kind === b.kind ? 0 : a.kind === "term" ? -1 : 1) || a.order - b.order || (a.id < b.id ? -1 : 1));

  /** 켜진 규칙을 순서대로 담다가 한도를 넘으면 그 뒤는 모두 뺀다 */
  function plan() {
    const sent = new Set();
    let used = 0, full = false;
    for (const r of sorted()) {
      if (!r.enabled || full) continue;
      const n = lineOf(r).length + 1;
      if (used + n > BUDGET) { full = true; continue; }
      used += n; sent.add(r.id);
    }
    return { sent, used };
  }
  function promptBlock() {
    const { sent } = plan();
    const lines = sorted().filter((r) => sent.has(r.id)).map(lineOf);
    if (!lines.length) return "";
    return `

[팀 규칙]
이 페이지를 함께 쓰는 사람들이 정한 기준이다. 검색 범위, 포함·제외, 답변 방식에 반드시 반영하라. 용어 기준이 있는 말이 질문에 나오면 그 기준대로 보도자료를 고르고, 기준 때문에 뺀 보도자료가 있으면 답 끝에 "규칙에 따라 뺀 자료:" 뒤에 제목과 날짜를 짧게 적어라. 질문이 규칙과 다르게 분명히 요구하면 질문을 따르고 그렇게 했다고 한 줄 밝혀라.
${lines.join("\n")}`;
  }

  // ---- 화면 ----
  function setStatus(text) { const s = $("ru-status"); s.textContent = text; s.hidden = !text; }
  const canTry = () => !!db && writable !== false;
  function applyWritable() {
    $("ru-add").hidden = !canTry() || !$("ru-form").hidden;
    if (!db) return;
    if (writable === false) { closeForm(); setStatus("보기만 할 수 있습니다. 규칙을 고치려면 페이지 소유자에게 편집 권한을 요청하세요."); }
    else if (writable === true) setStatus("편집할 수 있습니다. 바꾼 내용은 이 페이지를 쓰는 모두에게 바로 반영됩니다.");
  }
  /** 쓰기 실패 → 안내 문구. 권한 거절이면 이번 방문 동안 읽기 전용으로 바꾼다 */
  function refused(e) {
    const code = e && e.code;
    if (code === "invalid_argument") { writable = false; applyWritable(); render(); return "편집 권한이 없어 저장하지 못했습니다."; }
    if (code === "quota_exceeded") return "저장 공간이 가득 찼습니다. 쓰지 않는 규칙을 지운 뒤 다시 해 보세요.";
    if (code === "resource_exhausted") return "요청이 너무 잦습니다. 잠시 뒤 다시 해 보세요.";
    if (code === "revoked") return "이 페이지 접근 권한이 바뀌었습니다. 새로 고쳐 주세요.";
    return "저장하지 못했습니다. 잠시 뒤 다시 해 보세요.";
  }
  function formMsg(text) { const m = $("ru-form-msg"); m.textContent = text; m.hidden = !text; }
  function count() { $("ru-count").textContent = `내용 ${fmt($("ru-body").value.length)} / 1,000자`; }

  async function render() {
    const seq = ++renderSeq;
    const list = sorted();
    const { sent, used } = plan();
    $("ru-budget").textContent = db ? `켜진 규칙 ${fmt(rules.filter((r) => r.enabled).length)}개 · AI에 전달되는 분량 ${fmt(used)} / ${fmt(BUDGET)}자` : "";
    const note = $("ai-rules-note");
    if (sent.size) {
      const b = el("button", "textbtn", "규칙 보기"); b.type = "button";
      b.addEventListener("click", () => Tabs.show("rules"));
      note.replaceChildren(document.createTextNode(`팀 규칙 ${sent.size}개를 함께 전달합니다. `), b);
      note.hidden = false;
    } else note.hidden = true;
    if (!loaded) return;

    const ids = [...new Set([...list.flatMap((r) => [r.updatedBy, r.createdBy]), ...log.map((l) => l.by)])].filter((x) => x && x !== CLAUDE_ID);
    const names = user && ids.length ? await user.profiles(ids).catch(() => ({})) : {};
    if (seq !== renderSeq) return;
    const who = (id) => (id === CLAUDE_ID ? "Claude" : (names[id] && names[id].name) || (id && id === myId ? "나" : "누군가"));

    const box = $("ru-list");
    if (!list.length) box.replaceChildren(el("p", "empty", canTry() ? "아직 규칙이 없습니다. ‘규칙 추가’로 첫 규칙을 적어 보세요." : "아직 규칙이 없습니다."));
    else box.replaceChildren(...list.map((r) => card(r, sent.has(r.id), who)));

    const ul = $("ru-log");
    if (!log.length) ul.replaceChildren(el("li", null, "아직 기록이 없습니다."));
    else ul.replaceChildren(...log.map((l) => logItem(l, who)));
  }

  function card(r, isSent, who) {
    const art = el("article", "ru-card" + (r.enabled ? "" : " off"));
    const head = el("div", "ru-head");
    head.append(el("span", "chip", KIND[r.kind]), el("h4", null, r.title));
    const tg = el("label", "check ru-toggle");
    const cb = el("input"); cb.type = "checkbox"; cb.checked = r.enabled; cb.disabled = !canTry();
    cb.addEventListener("change", () => toggle(r, cb));
    tg.append(cb, document.createTextNode("AI에 적용"));
    head.appendChild(tg);
    art.append(head, el("p", "ru-body", r.body));
    if (r.enabled && !isSent) art.appendChild(el("p", "note warn", "전체 분량을 넘어 지금은 AI에 전달되지 않습니다. 다른 규칙을 줄이거나 꺼 주세요."));
    if (r.example) {
      const ex = el("div", "ru-ex");
      const t = el("button", "btn-ghost", "이 질문으로 시험"); t.type = "button";
      t.addEventListener("click", () => { Tabs.show("ai"); AI.ask(r.example); });
      ex.append(el("span", null, `예시 질문: ${r.example}`), t);
      art.appendChild(ex);
    }
    const foot = el("div", "ru-foot");
    foot.appendChild(el("span", "note num", [when(r.updatedAt), `${who(r.updatedBy)} ${r.createdAt === r.updatedAt ? "작성" : "수정"}`].filter(Boolean).join(" · ")));
    if (canTry()) {
      const acts = el("div", "acts");
      const ed = el("button", "btn-ghost", "고치기"); ed.type = "button";
      ed.addEventListener("click", () => openForm(r));
      const del = el("button", "btn-ghost", "삭제"); del.type = "button";
      del.addEventListener("click", () => remove(r, del));
      acts.append(ed, del);
      foot.appendChild(acts);
    }
    art.appendChild(foot);
    return art;
  }
  function logItem(l, who) {
    const li = el("li");
    li.appendChild(el("span", "num", `${when(l.at)} · ${who(l.by)} · ‘${l.title}’ ${ACTION[l.action] || "변경"}`));
    if (l.before && canTry()) {
      const b = el("button", "btn-ghost", "이 변경 전으로 되돌리기"); b.type = "button";
      b.addEventListener("click", () => restore(l, b));
      li.appendChild(b);
    }
    return li;
  }

  // ---- 쓰기 (문서마다 한 번에 하나씩) ----
  async function addLog(ruleId, action, title, before, after) {
    try { await db.collection("rules_log").add({ ruleId, action, title, before, after, by: myId, at: new Date().toISOString() }); }
    catch { /* 기록 실패는 규칙 저장을 막지 않는다 */ }
  }
  function openForm(r = null) {
    editing = r ? { id: r.id, base: r.updatedAt, confirmed: false } : null;
    $("ru-form-title").textContent = r ? `‘${r.title}’ 고치기` : "새 규칙";
    for (const radio of document.querySelectorAll("input[name=ru-kind]")) radio.checked = radio.value === (r ? r.kind : "term");
    $("ru-title").value = r ? r.title : "";
    $("ru-body").value = r ? r.body : "";
    $("ru-example").value = r ? r.example : "";
    formMsg("");
    count();
    $("ru-form").hidden = false;
    $("ru-add").hidden = true;
    $("ru-form").scrollIntoView({ block: "nearest" });
    $("ru-title").focus();
  }
  function closeForm() {
    $("ru-form").hidden = true;
    editing = null;
    $("ru-add").hidden = !canTry();
  }
  async function save(e) {
    e.preventDefault();
    const kind = (document.querySelector("input[name=ru-kind]:checked") || {}).value === "style" ? "style" : "term";
    const title = $("ru-title").value.trim(), body = $("ru-body").value.trim(), example = $("ru-example").value.trim();
    if (!title || !body) { formMsg("이름과 내용을 적어 주세요."); return; }
    const btn = $("ru-save");
    btn.disabled = true;
    const now = new Date().toISOString();
    try {
      if (editing) {
        const ref = db.doc("rules/" + editing.id);
        const cur = await ref.get();
        const prev = cur.exists ? normalize(cur.id, cur.data()) : null;
        if (!editing.confirmed && (!prev || prev.updatedAt !== editing.base)) {
          editing.confirmed = true;
          formMsg(prev ? "편집하는 동안 다른 사람이 이 규칙을 고쳤습니다. 아래 목록에서 새 내용을 확인하세요. ‘저장’을 한 번 더 누르면 지금 쓴 내용으로 덮어씁니다."
            : "편집하는 동안 이 규칙이 지워졌습니다. ‘저장’을 한 번 더 누르면 다시 만듭니다.");
          return;
        }
        const next = { kind, title, body, example, enabled: prev ? prev.enabled : true, order: prev ? prev.order : Date.now(),
          createdBy: prev ? prev.createdBy : myId, createdAt: prev ? prev.createdAt : now, updatedBy: myId, updatedAt: now };
        await ref.set(next);
        await addLog(editing.id, prev ? "update" : "create", title, prev && bodyOf(prev), next);
      } else {
        const ref = db.collection("rules").doc();
        const next = { kind, title, body, example, enabled: true, order: Date.now(), createdBy: myId, createdAt: now, updatedBy: myId, updatedAt: now };
        await ref.set(next);
        await addLog(ref.id, "create", title, null, next);
      }
      closeForm();
      toast("저장했습니다. 다음 질문부터 반영됩니다.");
    } catch (err) {
      formMsg(refused(err));
    } finally {
      btn.disabled = false;
    }
  }
  async function toggle(r, cb) {
    cb.disabled = true;
    const now = new Date().toISOString();
    try {
      await db.doc("rules/" + r.id).update({ enabled: cb.checked, updatedBy: myId, updatedAt: now });
      await addLog(r.id, cb.checked ? "on" : "off", r.title, bodyOf(r), { ...bodyOf(r), enabled: cb.checked, updatedBy: myId, updatedAt: now });
    } catch (err) {
      cb.checked = !cb.checked;
      toast(refused(err));
    } finally {
      cb.disabled = !canTry();
    }
  }
  async function remove(r, btn) {
    if (deleteArm !== r.id) {
      deleteArm = r.id;
      btn.textContent = "한 번 더 누르면 삭제";
      setTimeout(() => { if (deleteArm === r.id) { deleteArm = null; btn.textContent = "삭제"; } }, 4000);
      return;
    }
    deleteArm = null;
    btn.disabled = true;
    try {
      await db.doc("rules/" + r.id).delete();
      await addLog(r.id, "delete", r.title, bodyOf(r), null);
      toast(`‘${r.title}’ 규칙을 지웠습니다. 변경 기록에서 되돌릴 수 있습니다.`);
    } catch (err) {
      btn.disabled = false;
      toast(refused(err));
    }
  }
  async function restore(l, btn) {
    btn.disabled = true;
    try {
      const ref = db.doc("rules/" + l.ruleId);
      const cur = await ref.get();
      const prev = cur.exists ? bodyOf(normalize(cur.id, cur.data())) : null;
      const next = { ...bodyOf(normalize(l.ruleId, l.before)), updatedBy: myId, updatedAt: new Date().toISOString() };
      await ref.set(next);
      await addLog(l.ruleId, "restore", next.title, prev, next);
      toast(`‘${next.title}’ 규칙을 그 변경 전 상태로 되돌렸습니다.`);
    } catch (err) {
      btn.disabled = false;
      toast(refused(err));
    }
  }

  async function init() {
    $("ru-add").addEventListener("click", () => openForm());
    $("ru-cancel").addEventListener("click", closeForm);
    $("ru-form").addEventListener("submit", save);
    $("ru-body").addEventListener("input", count);
    const use = (n) => (window.claude && typeof window.claude.use === "function" ? window.claude.use(n) : Promise.resolve(null)).catch(() => null);
    [db, user] = await Promise.all([use("db"), use("user")]);
    if (!db) {
      $("ru-list").replaceChildren(el("p", "empty", "claude.ai에 로그인한 상태로 이 페이지를 열면 팀 규칙을 보고 고칠 수 있습니다."));
      return;
    }
    if (user) { myId = await user.id(); writable = await user.can("data.write"); }
    applyWritable();
    const failed = (e) => {
      setStatus(e && e.code === "revoked" ? "이 페이지 접근 권한이 바뀌었습니다. 새로 고쳐 주세요." : "규칙을 불러오지 못했습니다. 새로 고쳐 주세요.");
    };
    db.collection("rules").onSnapshot((snap) => {
      rules = snap.docs.filter((d) => d.exists).map((d) => normalize(d.id, d.data()));
      loaded = true;
      render();
    }, failed);
    db.collection("rules_log").orderBy("at", "desc").limit(40).onSnapshot((snap) => {
      log = snap.docs.filter((d) => d.exists).map((d) => {
        const x = d.data();
        return { ruleId: str(x.ruleId, 200), action: str(x.action, 20), title: str(x.title, 40), before: x.before && typeof x.before === "object" ? x.before : null, by: x.by || null, at: str(x.at, 40) };
      }).filter((l) => l.ruleId);
      render();
    }, () => {});
  }
  return { init, promptBlock, show() {}, resize() {} };
})();
