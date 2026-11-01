// 포인터 이벤트 → 렌즈 상태(위치/강도). 보간은 step()에서 매 프레임.

export function createLensController(canvas, isOverMap) {
  const lens = {
    targetX: 0, targetY: 0, x: 0, y: 0,
    targetStrength: 0, strength: 0,
  };
  let touchDown = false;

  const toLocal = (e) => {
    const r = canvas.getBoundingClientRect();
    return [e.clientX - r.left, e.clientY - r.top];
  };

  const moveTo = (x, y) => {
    lens.targetX = x;
    lens.targetY = y;
    // 렌즈가 꺼져 있다가 다시 켜질 때는 엉뚱한 곳에서 날아오지 않도록 바로 점프
    if (lens.strength < 0.02) { lens.x = x; lens.y = y; }
  };

  canvas.addEventListener("pointermove", (e) => {
    const [x, y] = toLocal(e);
    if (e.pointerType === "touch" && !touchDown) return;
    const over = isOverMap(x, y);
    if (over) moveTo(x, y);
    lens.targetStrength = over ? 1 : 0;
  });

  canvas.addEventListener("pointerdown", (e) => {
    if (e.pointerType !== "touch") return;
    touchDown = true;
    canvas.setPointerCapture(e.pointerId);
    const [x, y] = toLocal(e);
    moveTo(x, y);
    lens.targetStrength = isOverMap(x, y) ? 1 : 0;
  });

  const release = (e) => {
    if (e.pointerType === "touch") touchDown = false;
    lens.targetStrength = 0;
  };
  canvas.addEventListener("pointerup", (e) => { if (e.pointerType === "touch") release(e); });
  canvas.addEventListener("pointercancel", release);
  canvas.addEventListener("pointerleave", release);

  // 한 프레임 진행. 화면을 다시 그려야 하면 true
  function step(config) {
    const before = lens.x + lens.y * 7 + lens.strength * 1e4;
    lens.x += (lens.targetX - lens.x) * config.FOLLOW;
    lens.y += (lens.targetY - lens.y) * config.FOLLOW;
    lens.strength += (lens.targetStrength - lens.strength) * config.FADE;
    if (Math.abs(lens.targetStrength - lens.strength) < 0.001) lens.strength = lens.targetStrength;
    if (Math.abs(lens.targetX - lens.x) < 0.05) lens.x = lens.targetX;
    if (Math.abs(lens.targetY - lens.y) < 0.05) lens.y = lens.targetY;
    const after = lens.x + lens.y * 7 + lens.strength * 1e4;
    return before !== after;
  }

  return { lens, step };
}
