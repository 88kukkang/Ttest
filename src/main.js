import { CONFIG } from "./config.js";
import { buildGrid } from "./grid.js";
import { createLens, lensReach } from "./fisheye.js";
import { draw } from "./renderer.js";
import { createLensController } from "./interaction.js";

const canvas = document.getElementById("map");
const hud = document.getElementById("hud");
const ctx = canvas.getContext("2d");

const config = { ...CONFIG };
let geojson = null;
let grid = null;
let labels = [];
let width = 0, height = 0;
let apply = null, reach = 0;
let hoverId = null;
let dirty = true;

// 나중 기능(툴팁 등)을 붙일 자리
export let onHover = (cell) => {};

function rebuildLens() {
  config.LENS_RADIUS = grid.cellSize * config.LENS_RADIUS_CELLS;
  apply = createLens(config);
  reach = lensReach(config);
  dirty = true;
  updateHud();
}

function resize() {
  const dpr = window.devicePixelRatio || 1;
  width = canvas.clientWidth;
  height = canvas.clientHeight;
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  grid = buildGrid(geojson, width, height, config);
  labels = config.LABELS.map((l) => {
    const [x, y] = grid.project(l.lon, l.lat);
    return { ...l, x, y };
  });
  rebuildLens();
}

function isOverMap(x, y) {
  if (!grid) return false;
  const m = grid.cellSize * 2;
  const b = grid.box;
  return x > b.x0 - m && x < b.x1 + m && y > b.y0 - m && y < b.y1 + m;
}

function updateHud(cell = grid?.cellAt(controller.lens.targetX, controller.lens.targetY)) {
  const mode = config.LENS_FALLOFF === "soft" ? "soft (반경 밖까지 퍼짐)" : "hard (반경 안만)";
  const where = controller.lens.targetStrength > 0 && cell ? ` · ${cell.region}` : "";
  hud.textContent = `렌즈: ${mode} — L 키로 전환${where}`;
}

const controller = createLensController(canvas, isOverMap);

function frame() {
  const moved = controller.step(config);
  const lens = controller.lens;

  const cell = lens.targetStrength > 0 ? grid.cellAt(lens.targetX, lens.targetY) : null;
  const id = cell?.id ?? null;
  if (id !== hoverId) {
    hoverId = id;
    onHover(cell);
    updateHud(cell);
    dirty = true;
  }

  if (moved || dirty) {
    draw(ctx, { width, height, grid, lens, apply, reach, config, hoverId, labels });
    dirty = false;
  }
  requestAnimationFrame(frame);
}

window.addEventListener("keydown", (e) => {
  if (e.key === "l" || e.key === "L" || e.key === "ㅣ") {
    config.LENS_FALLOFF = config.LENS_FALLOFF === "soft" ? "hard" : "soft";
    rebuildLens();
  }
});

let resizeTimer = 0;
new ResizeObserver(() => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { if (geojson) resize(); }, 150);
}).observe(canvas);

geojson = await (await fetch("data/korea-provinces.geo.json")).json();
resize();
requestAnimationFrame(frame);
