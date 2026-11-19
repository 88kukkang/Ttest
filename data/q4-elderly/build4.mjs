import fs from 'fs';
import * as topo from 'topojson-client';
import { geoMercator, geoPath } from 'd3-geo';
import * as simp from 'topojson-simplify';
const r1 = (n) => Math.round(n * 10) / 10;
const shrink = (d) => d ? d.replace(/-?\d+\.\d+/g, (m) => String(Math.round(+m))) : d;
const M = JSON.parse(fs.readFileSync('skorea-municipalities-2018-topo-simple.json'));
const P = JSON.parse(fs.readFileSync('skorea-provinces-2018-topo-simple.json'));
const Ms = simp.simplify(simp.presimplify(M), simp.quantile(simp.presimplify(M), +(process.argv[2] || 0.25)));
const Ps = simp.simplify(simp.presimplify(P), simp.quantile(simp.presimplify(P), +(process.argv[2] || 0.25)));
const mun = topo.feature(Ms, M.objects.skorea_municipalities_2018_geo).features;
const prov = topo.feature(Ps, P.objects.skorea_provinces_2018_geo).features;
// mainland + Jeju; Ulleung/Dokdo kept (they sit inside the extent at the right edge)
const proj = geoMercator().fitExtent([[8, 8], [592, 712]], { type: 'FeatureCollection', features: topo.feature(P, P.objects.skorea_provinces_2018_geo).features });
const path = geoPath(proj);
const units = mun.map((f) => ({ code: f.properties.code, name: f.properties.name, d: shrink(path(f)), c: path.centroid(f).map(r1), a: r1(path.area(f)) }));
const sido = prov.map((f) => ({ code: f.properties.code, name: f.properties.name, d: shrink(path(f)) }));
fs.writeFileSync('kor_mun.json', JSON.stringify({ units, sido, W: 600, H: 720 }));
console.log(units.length, JSON.stringify({ units, sido }).length);
