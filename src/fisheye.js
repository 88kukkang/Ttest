// 순수 함수 모음: DOM/캔버스에 의존하지 않는다.
// 모든 렌즈는 apply(px, py, fx, fy, strength) → { x, y, z } 형태.
//   px,py: 원래 점, fx,fy: 렌즈 중심, strength: 0~1, z: 크기 배율

export function createLens(config) {
  return config.LENS_FALLOFF === "soft" ? createSoftLens(config) : createHardLens(config);
}

// 렌즈가 셀을 움직일 수 있는 최대 거리(이 밖은 계산 생략 가능)
export function lensReach(config) {
  return config.LENS_FALLOFF === "soft"
    ? config.LENS_RADIUS * config.SOFT_SPREAD
    : config.LENS_RADIUS;
}

// soft: 효과가 반경 밖까지 퍼지고, 반경 x spread 에서 정확히 0 (기울기도 0)
export function createSoftLens({ LENS_RADIUS, SOFT_SPREAD, SOFT_AMOUNT }) {
  const outer = LENS_RADIUS * SOFT_SPREAD;
  const A = Math.min(SOFT_AMOUNT, 1.2); // 1.25 이상이면 셀 순서가 뒤집힘

  return function apply(px, py, fx, fy, strength = 1) {
    const dx = px - fx, dy = py - fy;
    const d = Math.hypot(dx, dy);
    if (d >= outer || strength <= 0) return { x: px, y: py, z: 1 };

    const t = d / outer;
    const w = (1 - t * t) ** 2;
    const s = 1 + A * strength * w;

    return { x: fx + dx * s, y: fy + dy * s, z: s };
  };
}

// hard: d3 circular fisheye 공식. 반경 안만 왜곡
export function createHardLens({ LENS_RADIUS: radius, DISTORTION: distortion, MAX_Z }) {
  const e = Math.exp(distortion);
  const k0 = (e / (e - 1)) * radius;
  const k1 = distortion / radius;

  return function apply(px, py, fx, fy, strength = 1) {
    const dx = px - fx, dy = py - fy;
    const dd = Math.hypot(dx, dy);
    if (dd >= radius || strength <= 0) return { x: px, y: py, z: 1 };
    const k = dd === 0
      ? MAX_Z
      : (k0 * (1 - Math.exp(-dd * k1))) / dd * 0.75 + 0.25;
    const r = { x: fx + dx * k, y: fy + dy * k, z: Math.min(k, MAX_Z) };
    return {
      x: px + (r.x - px) * strength,
      y: py + (r.y - py) * strength,
      z: 1 + (r.z - 1) * strength,
    };
  };
}
