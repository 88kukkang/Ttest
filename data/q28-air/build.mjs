import fs from 'fs';
import * as topo from 'topojson-client';
import { geoAzimuthalEquidistant, geoPath, geoMercator, geoDistance, geoCircle } from 'd3-geo';
const r1 = (n) => Math.round(n * 10) / 10;
const shrink = (d) => d ? d.replace(/-?\d+\.\d+/g, (m) => String(r1(+m))) : d;
const W = JSON.parse(fs.readFileSync('node_modules/world-atlas/countries-110m.json'));
const countries = topo.feature(W, W.objects.countries).features;
const SEOUL = [126.98, 37.57];
const R = 380, C = 400, maxAngle = 120;
const proj = geoAzimuthalEquidistant().rotate([-SEOUL[0], -SEOUL[1]]).clipAngle(maxAngle).scale(R / (maxAngle * Math.PI / 180)).translate([C, C]).precision(0.3);
const path = geoPath(proj);
const names = new Set(countries.map((f) => f.properties.name));
const dest = JSON.parse(fs.readFileSync('dest.json'));
const miss = Object.entries(dest).filter(([k, v]) => v[0] && !names.has(v[0])).map(([k, v]) => k + ':' + v[0]);
console.error('unmatched', miss);
const world = countries.map((f) => ({ n: f.properties.name, d: shrink(path(f)) })).filter((c) => c.d);
const outline = shrink(path({ type: 'Sphere' }));
const rings = [2000, 4000, 6000, 8000, 10000, 12000].map((km) => ({ km, r: r1(km / 6371 * R / (maxAngle * Math.PI / 180)) }));
const pts = {};
for (const [k, [en, lat, lon, city]] of Object.entries(dest)) {
  const p = proj([lon, lat]); const km = Math.round(geoDistance(SEOUL, [lon, lat]) * 6371);
  pts[k] = { en, city, km, xy: p ? [r1(p[0]), r1(p[1])] : null };
}
// Korea inset with 50m outlines
const W50 = JSON.parse(fs.readFileSync('node_modules/world-atlas/countries-50m.json'));
const c50 = topo.feature(W50, W50.objects.countries).features;
const kp = geoMercator().fitExtent([[10, 10], [350, 430]], { type: 'LineString', coordinates: [[124.6, 33.1], [131.0, 38.7]] });
const kpath = geoPath(kp);
const korea = c50.filter((f) => ['South Korea', 'North Korea', 'Japan', 'China'].includes(f.properties.name)).map((f) => ({ n: f.properties.name, d: shrink(kpath(f)) }));
const AP = { '인천(ICN)': [126.44, 37.46], '김포(GMP)': [126.80, 37.56], '제주(CJU)': [126.49, 33.51], '김해(PUS)': [128.94, 35.18], '대구(TAE)': [128.66, 35.89], '청주(CJJ)': [127.50, 36.72], '광주(KWJ)': [126.81, 35.13], '무안(MWX)': [126.38, 34.99], '여수(RSU)': [127.62, 34.84], '울산(USN)': [129.35, 35.59], '사천(HIN)': [128.07, 35.09], '포항경주(KPO)': [129.42, 35.99], '군산(KUV)': [126.62, 35.90], '원주(WJU)': [127.96, 37.44], '양양(YNY)': [128.67, 38.06] };
const airports = Object.fromEntries(Object.entries(AP).map(([k, ll]) => [k, kp(ll).map(r1)]));
fs.writeFileSync('geo.json', JSON.stringify({ world, outline, rings, pts, seoul: proj(SEOUL).map(r1), korea, airports }));
console.error('size', fs.statSync('geo.json').size);
