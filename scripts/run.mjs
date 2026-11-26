// Canberra playgrounds: Plotlay's engine on the prepared tables. Builds the project the example opens (playgrounds,
// mesh blocks with their children, the 5-minute walk from every playground with the crow-flies distance beside it, the
// walk kept for the Flow look so it can grow minute by minute, and 400 m circles), and writes the numbers.
//   node scripts/run.mjs <plotlay worktree> <build dir>
// The OpenStreetMap ways come from the Geofabrik extract of 22 November 2026 (scripts/osm_elements.mjs, the same filter
// as the app's Overpass query), so the numbers are reproducible; the boxes the app would fetch are listed for the record.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';
const [PL, B] = process.argv.slice(2);
const imp = (f) => import(pathToFileURL(path.join(PL, f)).href);
const A = await imp('src/core/agent.js'), D = await imp('src/core/datalayers.js'), C = await imp('src/core/catchment.js'), W = await imp('src/core/walkers.js');
const pc = (await import(pathToFileURL(path.join(PL, 'node_modules/polygon-clipping/dist/polygon-clipping.esm.js')).href)).default;
const T = (f) => JSON.parse(fs.readFileSync(path.join(B, 'tables', f), 'utf8'));
const t0 = Date.now(), log = (m) => console.log(`${((Date.now() - t0) / 1000).toFixed(1)}s ${m}`);

const pg = T('playgrounds.geojson'), mb = T('meshblocks.geojson');
const p = A.newProject({ name: 'Canberra playgrounds within a five-minute walk', lat: -35.30, lng: 149.11 });
const f = A.frameOf(p);
const g = D.createDataLayer(p, { name: 'Playgrounds', prefix: 'PLGR' });
const title = (s) => String(s || '').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
D.addDataShapes(p, { layer: g.id, order: 'as-is', shareKeys: true, src: { kind: 'given', source: 'ACT Government, ACTGOV Playground Assets (CC BY 4.0)' },
    shapes: pg.features.map((x) => ({ point: f.toM([x.geometry.coordinates[1], x.geometry.coordinates[0]]), key: x.properties.asset_id,
        props: { name: title(x.properties.location), kind: title(x.properties.asset_sub_type), shade: title(x.properties.shade_level), suburb: title(x.properties.suburb), surface_m2: x.properties.surface_area } })) });
const m = D.createDataLayer(p, { name: 'Mesh blocks', prefix: 'MB' });
D.addDataShapes(p, { layer: m.id, order: 'as-is', shareKeys: true, src: { kind: 'given', source: 'ABS ASGS 2021 mesh blocks and 2021 Census counts (CC BY 4.0)' },
    shapes: mb.features.map((x) => { const rs = x.geometry.coordinates.map((r) => r.slice(0, -1).map(([ln, la]) => f.toM([la, ln]))); return { ring: rs[0], holes: rs.slice(1), key: x.properties.mb,
        props: { suburb: title(x.properties.suburb), district: x.properties.district, category: x.properties.category, dwellings: x.properties.dwellings, residents: x.properties.persons, children: x.properties.children } }; }) });
log(`layers: ${D.shapesOf(p, g).length} playgrounds, ${D.shapesOf(p, m).length} mesh blocks`);

// OpenStreetMap, one box at a time, kept
const OSM = path.join(B, 'raw', 'osm'); fs.mkdirSync(OSM, { recursive: true });
async function fetchAll(qs, tag) {
    const out = [];
    for (let i = 0; i < qs.length; i++) {
        const file = path.join(OSM, `${tag}-${crypto.createHash('sha1').update(qs[i]).digest('hex').slice(0, 10)}.json`);
        if (fs.existsSync(file)) { out.push(JSON.parse(fs.readFileSync(file, 'utf8'))); continue; }
        for (let k = 0; ; k++) {
            try { const els = await C.fetchOverpass(fetch, qs[i], { timeoutMs: 240000, userAgent: C.USER_AGENT }); fs.writeFileSync(file, JSON.stringify(els)); out.push(els); log(`${tag} box ${i + 1} of ${qs.length}: ${els.length} elements`); break; }
            catch (e) { if (k >= 4) throw e; log(`${tag} box ${i + 1}: ${e.message}, again in ${20 * (k + 1)} s`); await new Promise((r) => setTimeout(r, 20000 * (k + 1))); }
        }
        await new Promise((r) => setTimeout(r, 3000));
    }
    return out;
}
const qs = C.catchmentQueries(p, { layer: g.id, areas: m.id, minutes: 5 });
log(`${qs.length} boxes of streets`);
const ALL = JSON.parse(fs.readFileSync(path.join(OSM, 'elements.json'), 'utf8'));
const els = ALL.filter((e) => e.type === 'way');
log(`${els.length} ways from the extract`);
const res = {};
for (const minutes of [5, 10]) {
    const r = C.addWalkingCatchments(p, { layer: g.id, elements: els, minutes, measure: 'streets', areas: m.id, straight: true, people: 'children', name: `Playgrounds: ${minutes}-minute walk`, pc });
    log(`${minutes} min: children ${r.within.people_reached} of ${r.within.people_total} (${r.within.people_share}), crow flies ${r.within.people_straight_share}; streets ${r.within.reached_share}, straight ${r.within.straight_share}`);
    res[minutes] = { ...r, catchments: undefined, within: { ...r.within, areas: undefined } };
    // keep each mesh block's answer for this walk under its own names (the next run writes the plain names again)
    const rows = r.within.areas.map((o) => ({ key: o.key, [`reached_pct_${minutes}`]: o.reached_pct, [`straight_pct_${minutes}`]: o.straight_pct, [`children_reached_${minutes}`]: o.people_reached, [`children_straight_${minutes}`]: o.people_straight }));
    D.setValues(p, { layer: m.id, rows });
    fs.writeFileSync(path.join(B, 'tables', `areas_${minutes}.json`), JSON.stringify(r.within.areas));
    fs.writeFileSync(path.join(B, 'tables', `catchments_${minutes}.json`), JSON.stringify(r.catchments));
}
fs.writeFileSync(path.join(B, 'tables', 'engine.json'), JSON.stringify(res, null, 1));

// the walk kept for the Flow look: every playground together, 10 minutes at 4.8 km/h
const wq = W.walkersQueries(p, { layer: g.id, minutes: 10, walkers: [{ kmh: 4.8, name: 'Walking at 4.8 km/h' }] });
log(`${wq.length} boxes for the walk`);
const wels = ALL;
const wr = W.addWalkerCatchments(p, { layer: g.id, elements: wels, minutes: 10, walkers: [{ kmh: 4.8, name: 'Walking at 4.8 km/h' }], name: 'The walk from every playground', pc });
log(`walkers: ${JSON.stringify(wr.walkers.map((x) => [x.walker, x.area_km2, x.street_km]))}`);
fs.writeFileSync(path.join(B, 'app', 'engine-project.json'), JSON.stringify({ format: 'map-overlay-project', version: 1, project: p, blobs: {} }));
log(`project ${Math.round(fs.statSync(path.join(B, 'app', 'engine-project.json')).size / 1e6)} MB`);
