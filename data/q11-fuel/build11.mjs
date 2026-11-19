import fs from 'fs';
import * as topo from 'topojson-client';
import * as simp from 'topojson-simplify';
import { geoMercator, geoPath } from 'd3-geo';
// KATEC (TM128, Bessel) -> lon/lat (no datum shift; ~300 m off, below one pixel here)
const a = 6377397.155, f = 1 / 299.1528128, e2 = 2 * f - f * f, ep2 = e2 / (1 - e2), k0 = 0.9999, lat0 = 38 * Math.PI / 180, lon0 = 128 * Math.PI / 180, FE = 400000, FN = 600000;
const M = (p) => a * ((1 - e2 / 4 - 3 * e2 * e2 / 64 - 5 * e2 ** 3 / 256) * p - (3 * e2 / 8 + 3 * e2 * e2 / 32 + 45 * e2 ** 3 / 1024) * Math.sin(2 * p) + (15 * e2 * e2 / 256 + 45 * e2 ** 3 / 1024) * Math.sin(4 * p) - (35 * e2 ** 3 / 3072) * Math.sin(6 * p));
function inv(x, y) {
  const m = M(lat0) + (y - FN) / k0, mu = m / (a * (1 - e2 / 4 - 3 * e2 * e2 / 64 - 5 * e2 ** 3 / 256)), e1 = (1 - Math.sqrt(1 - e2)) / (1 + Math.sqrt(1 - e2));
  const p1 = mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * Math.sin(2 * mu) + (21 * e1 * e1 / 16 - 55 * e1 ** 4 / 32) * Math.sin(4 * mu) + (151 * e1 ** 3 / 96) * Math.sin(6 * mu);
  const C1 = ep2 * Math.cos(p1) ** 2, T1 = Math.tan(p1) ** 2, N1 = a / Math.sqrt(1 - e2 * Math.sin(p1) ** 2), R1 = a * (1 - e2) / (1 - e2 * Math.sin(p1) ** 2) ** 1.5, D = (x - FE) / (N1 * k0);
  const lat = p1 - (N1 * Math.tan(p1) / R1) * (D * D / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 * C1 - 9 * ep2) * D ** 4 / 24 + (61 + 90 * T1 + 298 * C1 + 45 * T1 * T1 - 252 * ep2 - 3 * C1 * C1) * D ** 6 / 720);
  const lon = lon0 + (D - (1 + 2 * T1 + C1) * D ** 3 / 6 + (5 - 2 * C1 + 28 * T1 - 3 * C1 * C1 + 8 * ep2 + 24 * T1 * T1) * D ** 5 / 120) / Math.cos(p1);
  return [lon * 180 / Math.PI, lat * 180 / Math.PI];
}
const P = JSON.parse(fs.readFileSync('skorea-provinces-2018-topo-simple.json'));
const full = topo.feature(P, P.objects.skorea_provinces_2018_geo).features;
const Ps = simp.simplify(simp.presimplify(P), simp.quantile(simp.presimplify(P), 0.1));
const prov = topo.feature(Ps, Ps.objects.skorea_provinces_2018_geo).features;
const proj = geoMercator().fitExtent([[8, 8], [592, 712]], { type: 'FeatureCollection', features: full });
const path = geoPath(proj);
const S = JSON.parse(fs.readFileSync(process.argv[2]));
const st = S.rows.map((r) => { const [lo, la] = inv(+r.x, +r.y); const [px, py] = proj([lo, la]); return [Math.round(px * 2) / 2, Math.round(py * 2) / 2]; });
const sido = prov.map((f) => ({ n: f.properties.name, d: path(f).replace(/-?\d+\.\d+/g, (m) => String(Math.round(+m))) }));
fs.writeFileSync('kor_st.json', JSON.stringify({ sido, xy: st, W: 600, H: 720 }));
console.log(st.length, st.slice(0, 3), JSON.stringify(sido).length);
