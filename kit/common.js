  const NS = "http://www.w3.org/2000/svg";
  const s = (tag, a = {}, p) => { const e = document.createElementNS(NS, tag); for (const k in a) if (a[k] != null) e.setAttribute(k, a[k]); if (p) p.append(e); return e; };
  const tx = (p, x, y, str, cls, size, anchor = "start", extra = {}) => { const t = s("text", { x, y, class: cls, "text-anchor": anchor, "font-size": size, ...extra }, p); t.textContent = str; return t; };
  const fmt = (n) => Math.round(n).toLocaleString("ko-KR");
  const f1 = (n) => n.toLocaleString("ko-KR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const pc = (n) => f1(n) + "%";
  const man = (n) => n >= 1e5 ? f1(n / 1e4).replace(/\.0$/, "") + "만" : fmt(n);
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const lerp = (arr, pos) => { const k = Math.floor(pos), f = pos - k; return k + 1 < arr.length ? arr[k] + (arr[k + 1] - arr[k]) * f : arr[k]; };
  const bEl = (t) => Object.assign(document.createElement("b"), { textContent: t });

  function table(id, head, rows) {
    const t = document.createElement("table"), th = document.createElement("thead"), tr = document.createElement("tr");
    head.forEach((h) => { const c = document.createElement("th"); c.textContent = h; tr.append(c); }); th.append(tr); t.append(th);
    const tb = document.createElement("tbody");
    rows.forEach((r) => { const row = document.createElement("tr"); r.forEach((v) => { const c = document.createElement("td"); c.textContent = v; row.append(c); }); tb.append(row); });
    t.append(tb); document.getElementById(id).replaceChildren(t);
  }
  function tipFor(fig) {
    const tip = fig.querySelector(".tip");
    return {
      show(ev, title, rows) {
        tip.replaceChildren(); const h = document.createElement("div"); h.className = "tn"; h.textContent = title; tip.append(h);
        rows.forEach(([v, k, col]) => { const d = document.createElement("div"); if (col) { const i = document.createElement("i"); i.className = "sw dot"; i.style.background = col; i.style.marginRight = "6px"; d.append(i); } const b = document.createElement("span"); b.className = "tv"; b.textContent = v + " "; const kk = document.createElement("span"); kk.textContent = k; d.append(b, kk); tip.append(d); });
        tip.hidden = false;
        const fr = fig.getBoundingClientRect(); let x, y;
        if (ev.clientX != null) { x = ev.clientX - fr.left + 14; y = ev.clientY - fr.top + 14; } else { const r = (ev.rect || ev.target.getBoundingClientRect()); x = r.right - fr.left + 8; y = r.top - fr.top; }
        const tw = tip.offsetWidth, th = tip.offsetHeight;
        if (x + tw > fr.width - 8) x = Math.max(8, x - tw - 28);
        if (y + th > fr.height - 8) y = Math.max(8, y - th - 28);
        tip.style.left = x + "px"; tip.style.top = y + "px";
      },
      hide() { tip.hidden = true; },
    };
  }
  /* Marks you can point at. One tab stop per chart; Left/Right step, Up/Down jump rows, Escape hides.
     pts: {x, y, r, fn() -> [title, rows]} in viewBox units; u = viewBox units per CSS px. */
  function pointLayer(v, tip, pts, label, u = 1) {
    const ring = s("circle", { class: "ring", "stroke-width": 2 * u, opacity: 0 }, v);
    let idx = -1;
    v.setAttribute("tabindex", "0"); v.setAttribute("aria-label", v.getAttribute("aria-label") + ". " + label);
    const show = (i, ev) => { idx = i; const p = pts[i]; ring.setAttribute("cx", p.x); ring.setAttribute("cy", p.y); ring.setAttribute("r", p.r + 4 * u); ring.setAttribute("opacity", 1); const [t, rows] = p.fn(); tip.show(ev || { target: ring }, t, rows); };
    const hide = () => { tip.hide(); ring.setAttribute("opacity", 0); };
    const nearest = (e) => {
      const r = v.getBoundingClientRect(), vb = v.viewBox.baseVal, k = vb.width / r.width;
      const x = vb.x + (e.clientX - r.left) * k, y = vb.y + (e.clientY - r.top) * k;
      let best = -1, bd = Infinity;
      pts.forEach((p, i) => { const d = Math.hypot(p.x - x, p.y - y) - p.r, reach = 18 * k; if (d < reach && d < bd) { bd = d; best = i; } });
      return best;
    };
    v.addEventListener("pointermove", (e) => { if (e.pointerType === "touch") return; const b = nearest(e); if (b >= 0) show(b, e); else hide(); });
    v.addEventListener("pointerdown", (e) => { const b = nearest(e); if (b >= 0) show(b, e); else hide(); });
    v.addEventListener("pointerleave", (e) => { if (e.pointerType !== "touch") hide(); });
    v.addEventListener("focus", () => { if (pts.length) show(idx < 0 ? 0 : idx); }); v.addEventListener("blur", hide);
    const vert = (dir) => { const c = pts[Math.max(idx, 0)]; let best = -1, bd = Infinity; pts.forEach((p, i) => { const dy = (p.y - c.y) * dir; if (dy <= 0.5) return; const d = dy * 3 + Math.abs(p.x - c.x); if (d < bd) { bd = d; best = i; } }); return best < 0 ? Math.max(idx, 0) : best; };
    v.addEventListener("keydown", (e) => {
      if (!pts.length) return;
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") { e.preventDefault(); show((Math.max(idx, 0) + (e.key === "ArrowRight" ? 1 : -1) + pts.length) % pts.length); }
      else if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); show(vert(e.key === "ArrowDown" ? 1 : -1)); }
      else if (e.key === "Escape") hide();
    });
  }
  /* A time cursor over a chart: pointer or Left/Right picks a time index, a vertical rule follows it. */
  function timeLayer(v, tip, n, xOf, y0, y1, fn, label, u = 1) {
    const rule = s("line", { y1: y0, y2: y1, stroke: "var(--ink)", "stroke-width": u, opacity: 0, "pointer-events": "none" }, v);
    let idx = -1;
    v.setAttribute("tabindex", "0"); v.setAttribute("aria-label", v.getAttribute("aria-label") + ". " + label);
    const show = (i, ev) => { idx = Math.max(0, Math.min(n - 1, i)); const x = xOf(idx); rule.setAttribute("x1", x); rule.setAttribute("x2", x); rule.setAttribute("opacity", .5); const [t, rows] = fn(idx); const r = v.getBoundingClientRect(), vb = v.viewBox.baseVal; tip.show(ev || { rect: { right: r.left + (x - vb.x) / vb.width * r.width, top: r.top + 20 } }, t, rows); };
    const hide = () => { tip.hide(); rule.setAttribute("opacity", 0); };
    const at = (e) => { const r = v.getBoundingClientRect(), vb = v.viewBox.baseVal; const x = vb.x + (e.clientX - r.left) * vb.width / r.width; let best = 0, bd = Infinity; for (let i = 0; i < n; i++) { const d = Math.abs(xOf(i) - x); if (d < bd) { bd = d; best = i; } } return best; };
    v.addEventListener("pointermove", (e) => { if (e.pointerType === "touch") return; show(at(e), e); });
    v.addEventListener("pointerdown", (e) => show(at(e), e));
    v.addEventListener("pointerleave", (e) => { if (e.pointerType !== "touch") hide(); });
    v.addEventListener("focus", () => show(idx < 0 ? n - 1 : idx)); v.addEventListener("blur", hide);
    v.addEventListener("keydown", (e) => { if (e.key === "ArrowRight" || e.key === "ArrowLeft") { e.preventDefault(); show(idx + (e.key === "ArrowRight" ? 1 : -1)); } else if (e.key === "Home") { e.preventDefault(); show(0); } else if (e.key === "End") { e.preventDefault(); show(n - 1); } else if (e.key === "Escape") hide(); });
  }
  /* A player: play/pause, scrubber and a large time readout. Frames 0..n-1; at rest it shows the last frame. */
  function Player(id, label, draw, n, labelOf, seconds = 10) {
    const box = document.getElementById(id);
    const btn = document.createElement("button"); btn.type = "button"; btn.className = "play"; btn.setAttribute("aria-label", label + " 재생");
    const icon = (playing) => { btn.replaceChildren(); const v = s("svg", { viewBox: "0 0 20 20", "aria-hidden": "true" }, btn); if (playing) { s("rect", { x: 4, y: 3, width: 4, height: 14, rx: 1, fill: "currentColor" }, v); s("rect", { x: 12, y: 3, width: 4, height: 14, rx: 1, fill: "currentColor" }, v); } else s("path", { d: "M5,3 L17,10 L5,17 Z", fill: "currentColor" }, v); };
    const yr = document.createElement("div"); yr.className = "yr"; yr.setAttribute("aria-hidden", "true");
    const sc = document.createElement("input"); sc.type = "range"; sc.className = "scrub"; sc.min = 0; sc.max = n - 1; sc.step = 1; sc.value = n - 1; sc.setAttribute("aria-label", label + " 시점");
    box.append(btn, yr, sc);
    let pos = n - 1, raf = 0, playing = false, t0 = 0, from = 0;
    const render = () => { const k = Math.min(n - 1, Math.floor(pos + 1e-6)); yr.textContent = labelOf(k); sc.value = Math.round(pos); sc.setAttribute("aria-valuetext", labelOf(Math.round(pos))); draw(pos); };
    const stop = () => { playing = false; cancelAnimationFrame(raf); icon(false); btn.setAttribute("aria-label", label + " 재생"); };
    const tick = (now) => { pos = Math.min(n - 1, from + (now - t0) / (seconds * 1000) * (n - 1)); render(); if (pos < n - 1) raf = requestAnimationFrame(tick); else stop(); };
    btn.addEventListener("click", () => {
      if (playing) { stop(); return; }
      if (reduce) { pos = n - 1; render(); return; }
      from = pos >= n - 1 ? 0 : pos; pos = from; playing = true; icon(true); btn.setAttribute("aria-label", label + " 멈춤");
      raf = requestAnimationFrame((t) => { t0 = t; tick(t); });
    });
    sc.addEventListener("input", () => { stop(); pos = +sc.value; render(); });
    icon(false);
    return { render, get pos() { return pos; } };
  }
  document.querySelectorAll(".opt").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll(".opt").forEach((o) => { o.setAttribute("aria-pressed", o === b); o.dataset.state = o.dataset.a === "1" ? "right" : "wrong"; });
    document.getElementById("reveal").hidden = false;
  }));
  function chips(id, opts, cur, onPick) {
    const box = document.getElementById(id);
    opts.forEach(([k, name]) => { const b = document.createElement("button"); b.type = "button"; b.className = "chip"; b.textContent = name; b.setAttribute("aria-pressed", k === cur); b.addEventListener("click", () => { box.querySelectorAll(".chip").forEach((x) => x.setAttribute("aria-pressed", x === b)); onPick(k); }); box.append(b); });
  }
  function onResize(fn) {
    let lastW = 0, rt;
    new ResizeObserver(() => { const w = document.querySelector(".page").clientWidth; if (Math.abs(w - lastW) < 2) return; lastW = w; clearTimeout(rt); rt = setTimeout(fn, 80); }).observe(document.querySelector(".page"));
  }
