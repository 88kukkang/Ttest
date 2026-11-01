window.KMap = window.KMap || {};

(function () {
  // 캔버스에 셀 그리기

  function rectPath(ctx, x, y, w, h, r) {
    if (r > 0 && ctx.roundRect) ctx.roundRect(x, y, w, h, Math.min(r, w / 2, h / 2));
    else ctx.rect(x, y, w, h);
  }

  function draw(ctx, state) {
    const { width, height, grid, lens, apply, reach, config, hoverId } = state;
    const { cells, cellSize } = grid;
    const fill = config.CELL_FILL;

    ctx.fillStyle = config.BG;
    ctx.fillRect(0, 0, width, height);

    const active = lens.strength > 0.001;
    const reach2 = (reach + cellSize) ** 2;
    const affected = [];

    // 1) 렌즈 영향 밖 셀: 색깔별로 묶어서 한 번에 채움
    const batches = new Map();
    for (const c of cells) {
      if (active) {
        const dx = c.x - lens.x, dy = c.y - lens.y;
        if (dx * dx + dy * dy < reach2) { affected.push(c); continue; }
      }
      if (c.id === hoverId) { affected.push(c); continue; }
      let list = batches.get(c.color);
      if (!list) batches.set(c.color, (list = []));
      list.push(c);
    }
    const s = cellSize * fill;
    for (const [color, list] of batches) {
      ctx.fillStyle = color;
      ctx.beginPath();
      for (const c of list) rectPath(ctx, c.x - s / 2, c.y - s / 2, s, s, config.CELL_RADIUS);
      ctx.fill();
    }

    // 2) 렌즈 영향 안 셀: 왜곡 적용 후 작은 것 → 큰 것 순서로 (큰 셀이 위로)
    const half = cellSize / 2;
    const items = affected.map((c) => {
      const p = apply(c.x, c.y, lens.x, lens.y, lens.strength);
      // 렌즈 가장자리에서는 셀이 반지름 방향으로 압축된다.
      // 그 압축률(유한차분)만큼 셀을 줄여야 서로 겹쳐 번지지 않는다.
      const dx = c.x - lens.x, dy = c.y - lens.y;
      const d = Math.hypot(dx, dy);
      if (d > 0) {
        const ux = dx / d, uy = dy / d, h = half;
        const a = apply(c.x - ux * h, c.y - uy * h, lens.x, lens.y, lens.strength);
        const b = apply(c.x + ux * h, c.y + uy * h, lens.x, lens.y, lens.strength);
        const radial = Math.hypot(b.x - a.x, b.y - a.y) / (2 * h);
        p.z = Math.min(p.z, Math.max(radial, 0.3));
      }
      let corners = null;
      if (config.MODE === "corners") {
        const h = half * fill;
        corners = [[-h, -h], [h, -h], [h, h], [-h, h]].map(([ox, oy]) => {
          const q = apply(c.x + ox, c.y + oy, lens.x, lens.y, lens.strength);
          return [q.x, q.y];
        });
      }
      return { c, p, corners };
    });
    items.sort((a, b) => a.p.z - b.p.z);

    for (const { c, p, corners } of items) {
      ctx.fillStyle = c.id === hoverId ? config.HOVER_COLOR : c.color;
      ctx.beginPath();
      if (corners) {
        ctx.moveTo(corners[0][0], corners[0][1]);
        for (let i = 1; i < 4; i++) ctx.lineTo(corners[i][0], corners[i][1]);
        ctx.closePath();
      } else {
        const size = s * p.z;
        rectPath(ctx, p.x - size / 2, p.y - size / 2, size, size, config.CELL_RADIUS * p.z);
      }
      ctx.fill();
    }

    // 3) 라벨 (렌즈를 통과시켜 함께 움직임)
    for (const label of state.labels) {
      const p = active ? apply(label.x, label.y, lens.x, lens.y, lens.strength) : { x: label.x, y: label.y, z: 1 };
      const fontSize = Math.round(Math.max(11, cellSize * 1.05) * Math.min(p.z, 1.6));
      const dot = Math.max(2.5, cellSize * 0.28) * Math.min(p.z, 1.6);
      ctx.font = `600 ${fontSize}px system-ui, -apple-system, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif`;
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.lineWidth = 3;
      ctx.strokeStyle = "rgba(239,237,233,0.85)";
      ctx.strokeText(label.text, p.x - dot * 2, p.y);
      ctx.fillStyle = "#1d1d1b";
      ctx.fillText(label.text, p.x - dot * 2, p.y);
      ctx.beginPath();
      ctx.arc(p.x, p.y, dot, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  KMap.draw = draw;
})();
