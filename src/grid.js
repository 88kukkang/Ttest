window.KMap = window.KMap || {};

(function () {
  // GeoJSON → 셀 배열.
  // 메르카토르 투영을 직접 계산한다(외부 라이브러리 없음, 폴리곤 감기 방향과 무관).

  const RAD = Math.PI / 180;
  const mercator = (lon, lat) => [lon * RAD, -Math.log(Math.tan(Math.PI / 4 + (lat * RAD) / 2))];

  function eachRing(geometry, fn) {
    const polys = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    for (const poly of polys) poly.forEach((ring, i) => fn(ring, i === 0));
  }

  function makeProjection(geojson, width, height, pad) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const f of geojson.features) {
      eachRing(f.geometry, (ring) => {
        for (const [lon, lat] of ring) {
          const [x, y] = mercator(lon, lat);
          if (x < x0) x0 = x; if (x > x1) x1 = x;
          if (y < y0) y0 = y; if (y > y1) y1 = y;
        }
      });
    }
    const scale = Math.min((width - 2 * pad) / (x1 - x0), (height - 2 * pad) / (y1 - y0));
    const ox = (width - (x1 - x0) * scale) / 2;
    const oy = (height - (y1 - y0) * scale) / 2;
    const project = (lon, lat) => {
      const [x, y] = mercator(lon, lat);
      return [ox + (x - x0) * scale, oy + (y - y0) * scale];
    };
    return {
      project,
      box: { x0: ox, y0: oy, x1: ox + (x1 - x0) * scale, y1: oy + (y1 - y0) * scale },
    };
  }

  function buildGrid(geojson, width, height, config) {
    const pad = Math.max(24, Math.min(width, height) * 0.06);
    const { project, box } = makeProjection(geojson, width, height, pad);

    const mapH = box.y1 - box.y0;
    const cellSize = Math.max(6, Math.min(16, Math.round(mapH / config.ROWS_TARGET)));

    // 시·도별 Path2D + 바운딩박스 (점 포함 판정용)
    const probe = document.createElement("canvas").getContext("2d");
    const regions = geojson.features.map((f) => {
      const path = new Path2D();
      let bx0 = Infinity, by0 = Infinity, bx1 = -Infinity, by1 = -Infinity;
      const ringCenters = [];
      eachRing(f.geometry, (ring, isOuter) => {
        let cx = 0, cy = 0;
        ring.forEach(([lon, lat], i) => {
          const [x, y] = project(lon, lat);
          i ? path.lineTo(x, y) : path.moveTo(x, y);
          if (x < bx0) bx0 = x; if (x > bx1) bx1 = x;
          if (y < by0) by0 = y; if (y > by1) by1 = y;
          cx += x; cy += y;
        });
        path.closePath();
        if (isOuter) ringCenters.push([cx / ring.length, cy / ring.length]);
      });
      return {
        name: f.properties.name ?? null,
        code: f.properties.code ?? null,
        path, bx0, by0, bx1, by1, ringCenters,
      };
    });

    const cols = Math.ceil((box.x1 - box.x0) / cellSize) + 1;
    const rows = Math.ceil((box.y1 - box.y0) / cellSize) + 1;
    const gx = box.x0 - ((cols * cellSize) - (box.x1 - box.x0)) / 2;
    const gy = box.y0 - ((rows * cellSize) - (box.y1 - box.y0)) / 2;

    const n = config.SAMPLES_PER_CELL;
    const regionAt = (x, y) => {
      for (let i = 0; i < regions.length; i++) {
        const r = regions[i];
        if (x < r.bx0 || x > r.bx1 || y < r.by0 || y > r.by1) continue;
        if (probe.isPointInPath(r.path, x, y, "evenodd")) return i;
      }
      return -1;
    };

    const byKey = new Map();
    const cells = [];
    const addCell = (col, row, regionIndex) => {
      const id = `${col}_${row}`;
      if (byKey.has(id)) return;
      const region = regions[regionIndex];
      const cell = {
        id, col, row,
        x: gx + (col + 0.5) * cellSize,
        y: gy + (row + 0.5) * cellSize,
        region: region.name,
        regionIndex,
        value: null,
        color: config.PALETTE[regionIndex % config.PALETTE.length],
      };
      byKey.set(id, cell);
      cells.push(cell);
    };

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        let hit = -1;
        for (let sy = 0; sy < n && hit < 0; sy++) {
          for (let sx = 0; sx < n && hit < 0; sx++) {
            const x = gx + (col + (sx + 0.5) / n) * cellSize;
            const y = gy + (row + (sy + 0.5) / n) * cellSize;
            hit = regionAt(x, y);
          }
        }
        if (hit >= 0) addCell(col, row, hit);
      }
    }

    // 샘플 사이로 빠진 아주 작은 섬(독도 등)도 셀 하나는 남긴다
    regions.forEach((r, i) => {
      for (const [x, y] of r.ringCenters) {
        const col = Math.floor((x - gx) / cellSize);
        const row = Math.floor((y - gy) / cellSize);
        if (col >= 0 && row >= 0 && col < cols && row < rows) addCell(col, row, i);
      }
    });

    return {
      cells,
      cellSize,
      project,
      box,
      // 화면 좌표 → 해당 위치의 셀 (왜곡 전 좌표 기준)
      cellAt(x, y) {
        return byKey.get(`${Math.floor((x - gx) / cellSize)}_${Math.floor((y - gy) / cellSize)}`) ?? null;
      },
    };
  }

  KMap.buildGrid = buildGrid;
})();
