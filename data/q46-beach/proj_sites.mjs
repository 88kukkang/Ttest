// Project lat/lon points into the 600x720 Korea frame used by q4/q19 maps (Mercator fitted to provinces).
import fs from 'fs';
import * as topo from 'topojson-client';
import { geoMercator } from 'd3-geo';
const P = JSON.parse(fs.readFileSync('skorea-provinces-2018-topo-simple.json'));
const proj = geoMercator().fitExtent([[8, 8], [592, 712]], { type: 'FeatureCollection', features: topo.feature(P, P.objects.skorea_provinces_2018_geo).features });
const pts = JSON.parse(fs.readFileSync(process.argv[2]));
console.log(JSON.stringify(pts.map(([n, lat, lon]) => [n, ...proj([lon, lat]).map((v) => Math.round(v * 10) / 10)])));
