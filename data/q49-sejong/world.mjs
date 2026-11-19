// World map (Equal Earth, 110m) for the cosmetics page: country outlines + centroids for the export destinations.
import fs from 'fs';
import * as topo from 'topojson-client';
import { geoEqualEarth, geoPath, geoCentroid } from 'd3-geo';
const r1 = (n) => Math.round(n * 10) / 10;
const shrink = (d) => d ? d.replace(/-?\d+\.\d+/g, (m) => String(r1(+m))) : d;
const W = JSON.parse(fs.readFileSync('node_modules/world-atlas/countries-110m.json'));
const fs110 = topo.feature(W, W.objects.countries).features.filter((f) => f.properties.name !== 'Antarctica');
const proj = geoEqualEarth().rotate([-150, 0]).fitSize([1000, 520], { type: 'FeatureCollection', features: fs110 });
const path = geoPath(proj);
const NAME = JSON.parse(fs.readFileSync(process.argv[2]));
const world = fs110.map((f) => ({ n: f.properties.name, d: shrink(path(f)) })).filter((c) => c.d);
const byEn = Object.fromEntries(fs110.map((f) => [f.properties.name, f]));
const EXTRA = { 'Hong Kong': [114.17, 22.32], 'Singapore': [103.82, 1.35], 'Macao': [113.54, 22.2], 'Bahrain': [50.55, 26.07], 'Mauritius': [57.55, -20.35] };
const pts = {};
for (const [ko, en] of Object.entries(NAME)) {
  let ll = EXTRA[en] || (byEn[en] ? geoCentroid(byEn[en]) : null);
  if (en === 'United States of America') ll = [-98, 39]; if (en === 'Russia') ll = [60, 57]; if (en === 'France') ll = [2.5, 46.5]; if (en === 'Canada') ll = [-100, 56]; if (en === 'Norway') ll = [9, 61];
  if (ll) pts[ko] = proj(ll).map(r1); else console.error('miss', ko, en);
}
const kor = proj([127.5, 36.5]).map(r1);
fs.writeFileSync(process.argv[3], JSON.stringify({ world, pts, kor, W: 1000, H: 520 }));
console.error('size', fs.statSync(process.argv[3]).size, Object.keys(pts).length);
