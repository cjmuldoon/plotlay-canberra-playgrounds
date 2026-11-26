# An independent check of the engine's walk and straight-line numbers, in plain Python: the same OpenStreetMap ways
# (raw/osm/elements.json), its own Dijkstra from every playground at once (joined at the nearest node within 120 m, that
# distance counted) and shapely's 400 m buffers for the straight line. Street length counted as the engine's measure
# 'streets' (roads and pedestrian streets, not parking aisles or driveways). Compares the totals with tables/engine.json.
#   python3 -I checks/check_walk.py   (from the build folder)
import json, math, heapq, os, sys
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree

B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
els = [e for e in json.load(open(os.path.join(B, 'raw/osm/elements.json'))) if e['type'] == 'way']
pg = json.load(open(os.path.join(B, 'tables/playgrounds.geojson')))['features']
eng = json.load(open(os.path.join(B, 'tables/engine.json')))
STREETS = {'living_street', 'pedestrian', 'residential', 'unclassified', 'tertiary', 'tertiary_link', 'secondary', 'secondary_link', 'primary', 'primary_link', 'road', 'service'}
def is_street(t): return t.get('highway') in STREETS and not (t.get('highway') == 'service' and t.get('service', '') in ('parking_aisle', 'driveway', 'drive-through', 'emergency_access'))
pts = [(f['geometry']['coordinates'][1], f['geometry']['coordinates'][0]) for f in pg]
lat0 = sum(p[0] for p in pts) / len(pts); lng0 = sum(p[1] for p in pts) / len(pts)
mx, my = 111320 * math.cos(lat0 * math.pi / 180), 111132
xy = lambda la, ln: ((ln - lng0) * mx, (la - lat0) * my)
node, adj, edges = {}, {}, []
for w in els:
    st = is_street(w.get('tags', {}))
    for (a, b, ga, gb) in zip(w['nodes'], w['nodes'][1:], w['geometry'], w['geometry'][1:]):
        pa, pb = xy(ga['lat'], ga['lon']), xy(gb['lat'], gb['lon'])
        node[a] = pa; node[b] = pb
        L = math.dist(pa, pb)
        if L == 0: continue
        edges.append((a, b, L, st)); adj.setdefault(a, []).append((b, L)); adj.setdefault(b, []).append((a, L))
total = sum(e[2] for e in edges if e[3])
# nearest node to each playground
ids = list(node); tree = STRtree([Point(node[i]) for i in ids])
starts = {}
for la, ln in pts:
    p = Point(xy(la, ln)); k = tree.nearest(p); d = p.distance(Point(node[ids[k]]))
    if d <= 120: starts[ids[k]] = min(starts.get(ids[k], 1e9), d)
def covered(metres):
    dist = dict(starts); h = [(d, n) for n, d in starts.items()]; heapq.heapify(h)
    while h:
        d, n = heapq.heappop(h)
        if d > dist.get(n, 1e18): continue
        for m, L in adj.get(n, ()):
            nd = d + L
            if nd <= metres and nd < dist.get(m, 1e18): dist[m] = nd; heapq.heappush(h, (nd, m))
    s = 0.0
    for a, b, L, st in edges:
        if not st: continue
        da, db = dist.get(a), dist.get(b)
        if da is None and db is None: continue
        ca = 0 if da is None else min(L, metres - da); cb = 0 if db is None else min(L, metres - db)
        s += L if ca + cb >= L else ca + cb
    return s
out = {}
for minutes in ('5', '10'):
    m = 400 if minutes == '5' else 800
    c = covered(m); e = eng[minutes]
    out[minutes] = {'python_covered_km': round(c / 1000, 1), 'engine_covered_km': round(e['covered_m'] / 1000, 1), 'python_network_km': round(total / 1000, 1), 'engine_network_km': round(e['network_m'] / 1000, 1)}
# straight line: street segments inside the union of 400 m circles
circles = unary_union([Point(xy(la, ln)).buffer(400, 64) for la, ln in pts])
lines = [LineString([node[a], node[b]]) for a, b, L, st in edges if st]
st_len = sum(l.intersection(circles).length for l in lines)
out['5']['python_straight_km'] = round(st_len / 1000, 1); out['5']['engine_straight_km'] = round(eng['5']['straight_m'] / 1000, 1)
ok = all(abs(v['python_covered_km'] - v['engine_covered_km']) <= max(0.5, 0.005 * v['engine_covered_km']) for v in out.values()) and abs(out['5']['python_straight_km'] - out['5']['engine_straight_km']) <= max(0.5, 0.005 * out['5']['engine_straight_km'])
out['agree'] = ok
json.dump(out, open(os.path.join(B, 'checks/check_walk.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
sys.exit(0 if ok else 1)
