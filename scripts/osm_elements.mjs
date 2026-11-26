// OpenStreetMap's walkable ways round Canberra, as the Overpass API answers Plotlay's walking query (out geom: each way
// with its node ids, geometry and tags), from the Geofabrik extract of 22 November 2026 instead of 40 requests to a busy
// Overpass server. The same filter as core/catchment.js queryWalkways: highway in WALKABLE, foot and access not no or
// private, not area=yes. With the crossings' and kerbs' nodes on them for walkers (core/walkers.js queryWalkers).
//   node scripts/osm_elements.mjs <plotlay worktree> <build dir>
// In: raw/osm/canberra-highways.opl (osmium extract -b 148.90,-35.55,149.30,-35.08, tags-filter w/highway n/kerb
// n/highway=crossing n/barrier=kerb, cat -f opl). Out: raw/osm/elements.json (ways and the tagged nodes).
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import { pathToFileURL } from 'node:url';
const [PL, B] = process.argv.slice(2);
const C = await import(pathToFileURL(path.join(PL, 'src/core/catchment.js')).href);
const ok = new Set(C.WALKABLE);
const unesc = (s) => s.replace(/%([0-9a-f]+)%/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)));
const tagsOf = (t) => { const o = {}; if (!t) return o; for (const kv of t.split(',')) { const i = kv.indexOf('='); if (i > 0) o[unesc(kv.slice(0, i))] = unesc(kv.slice(i + 1)); } return o; };
const xy = new Map(), nodeTags = new Map(), ways = [];
const rl = readline.createInterface({ input: fs.createReadStream(path.join(B, 'raw/osm/canberra-highways.opl')) });
for await (const line of rl) {
    const f = line.split(' '), id = +f[0].slice(1), get = (c) => (f.find((x) => x[0] === c) || '').slice(1);
    if (f[0][0] === 'n') {
        const x = +get('x'), y = +get('y'); if (Number.isFinite(x)) xy.set(id, [y, x]);
        const t = get('T'); if (t) { const tg = tagsOf(t); if (tg.kerb || tg.highway === 'crossing' || tg.barrier === 'kerb') nodeTags.set(id, tg); }
    } else if (f[0][0] === 'w') {
        const tg = tagsOf(get('T'));
        if (!ok.has(tg.highway) || /^(no|private)$/.test(tg.foot || '') || /^(no|private)$/.test(tg.access || '') || tg.area === 'yes') continue;
        ways.push({ id, nodes: get('N').split(',').filter(Boolean).map((n) => +n.slice(1)), tags: tg });
    }
}
const els = [], used = new Set();
for (const w of ways) {
    const geometry = w.nodes.map((n) => xy.get(n)).filter(Boolean).map(([lat, lon]) => ({ lat, lon }));
    if (geometry.length !== w.nodes.length || geometry.length < 2) continue;
    els.push({ type: 'way', id: w.id, nodes: w.nodes, geometry, tags: w.tags });
    for (const n of w.nodes) used.add(n);
}
let nodes = 0;
for (const [id, tg] of nodeTags) if (used.has(id)) { const [lat, lon] = xy.get(id); els.push({ type: 'node', id, lat, lon, tags: tg }); nodes++; }
fs.writeFileSync(path.join(B, 'raw/osm/elements.json'), JSON.stringify(els));
console.log(`${els.length - nodes} walkable ways, ${nodes} crossing and kerb nodes`);
