# Every number the Canberra playgrounds showcase quotes, from the engine's answer (tables/areas_<minutes>.json, one row a
# mesh block: its street length, how much is within the walk and within the same distance as the crow flies, and the
# children counted within each) and the prepared tables. Writes numbers.json and the CSV tables in tables/.
#   python3 -I py/numbers.py   (from the build folder)
import json, os
import pandas as pd, geopandas as gpd

B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = lambda f: os.path.join(B, 'tables', f)
mb = gpd.read_file(T('meshblocks.geojson')).rename(columns={'persons': 'residents'})
prep = json.load(open(T('prep.json'))); eng = json.load(open(T('engine.json')))
a5 = pd.DataFrame(json.load(open(T('areas_5.json')))).rename(columns={'key': 'mb'})
a10 = pd.DataFrame(json.load(open(T('areas_10.json')))).rename(columns={'key': 'mb'})
d = mb.drop(columns='geometry').merge(a5[['mb', 'network_m', 'reached_m', 'straight_m', 'reached_pct', 'straight_pct']], on='mb', how='left')
d = d.merge(a10[['mb', 'reached_m', 'straight_m']].rename(columns={'reached_m': 'reached10_m', 'straight_m': 'straight10_m'}), on='mb', how='left').fillna({'network_m': 0, 'reached_m': 0, 'straight_m': 0, 'reached10_m': 0, 'straight10_m': 0})
sh = lambda x: (x / d['network_m']).where(d['network_m'] > 0, 0).clip(upper=1)
d['walk5'], d['line5'], d['walk10'] = sh(d['reached_m']), sh(d['straight_m']), sh(d['reached10_m'])
for k in ('walk5', 'line5', 'walk10'):
    d[f'children_{k}'] = d['children'] * d[k]; d[f'residents_{k}'] = d['residents'] * d[k]
C = d['children'].sum()
r1 = lambda x: round(float(x), 1); pc = lambda a, b: r1(100 * a / b) if b else None
tot = {'children': round(C), 'residents': int(d['residents'].sum()), 'meshblocks': int(len(d)),
       'children_walk5': round(d['children_walk5'].sum()), 'children_line5': round(d['children_line5'].sum()), 'children_walk10': round(d['children_walk10'].sum()),
       'pct_walk5': pc(d['children_walk5'].sum(), C), 'pct_line5': pc(d['children_line5'].sum(), C), 'pct_walk10': pc(d['children_walk10'].sum(), C),
       'residents_pct_walk5': pc(d['residents_walk5'].sum(), d['residents'].sum()),
       'no_street_blocks': int((d['network_m'] == 0).sum()), 'no_street_children': round(d.loc[d['network_m'] == 0, 'children'].sum()),
       'none_in_reach_children': round(d.loc[(d['network_m'] > 0) & (d['walk5'] == 0), 'children'].sum()),
       'all_in_reach_children': round(d.loc[d['walk5'] >= 0.999, 'children'].sum())}
tot['children_gap'] = tot['children_line5'] - tot['children_walk5']
tot['children_not_walk5'] = tot['children'] - tot['children_walk5']
# check: the engine's own totals (people column 'children') agree with the sums here
assert abs(eng['5']['within']['people_reached'] - tot['children_walk5']) <= 1, (eng['5']['within'], tot)
assert abs(eng['5']['within']['people_straight'] - tot['children_line5']) <= 1
# by suburb and district
def grp(by):
    g = d.groupby(by).agg(children=('children', 'sum'), residents=('residents', 'sum'), children_walk5=('children_walk5', 'sum'), children_line5=('children_line5', 'sum'), children_walk10=('children_walk10', 'sum'),
                          network_m=('network_m', 'sum'), reached_m=('reached_m', 'sum')).reset_index()
    g['pct_walk5'] = (100 * g['children_walk5'] / g['children']).round(1); g['pct_line5'] = (100 * g['children_line5'] / g['children']).round(1)
    g['pct_walk10'] = (100 * g['children_walk10'] / g['children']).round(1); g['gap_pts'] = (g['pct_line5'] - g['pct_walk5']).round(1)
    for c in ('children', 'children_walk5', 'children_line5', 'children_walk10'): g[c] = g[c].round(0).astype(int)
    return g
sub = grp('suburb'); dis = grp('district')
pg = gpd.read_file(T('playgrounds.geojson'))
pg['suburb'] = pg['suburb'].str.title()
cnt = pg.groupby('suburb').size().rename('playgrounds').reset_index()
sub = sub.merge(cnt, on='suburb', how='left').fillna({'playgrounds': 0}); sub['playgrounds'] = sub['playgrounds'].astype(int)
sub['children_per_playground'] = (sub['children'] / sub['playgrounds'].where(sub['playgrounds'] > 0)).round(0)
big = sub[sub['children'] >= 300].copy()
low = big.sort_values('pct_walk5').head(10); high = big.sort_values('pct_walk5', ascending=False).head(10)
gap = big.sort_values('gap_pts', ascending=False).head(10)
sub.sort_values('children', ascending=False).to_csv(T('suburbs.csv'), index=False)
dis.sort_values('children', ascending=False).to_csv(T('districts.csv'), index=False)
# mesh blocks as a table (a point inside each for a map visual)
mbp = mb.copy(); mbp['geometry'] = mb.representative_point()
d['lat'] = mbp.geometry.y.round(6).values; d['lng'] = mbp.geometry.x.round(6).values
d['walk_band'] = pd.cut(d['walk5'], [-0.001, 0, 0.5, 0.999, 1.0], labels=['none of its streets', 'under half', 'half or more', 'all its streets']).astype(str)
d.loc[d['network_m'] == 0, 'walk_band'] = 'no streets mapped'
cols = ['mb', 'suburb', 'district', 'category', 'dwellings', 'residents', 'children', 'network_m', 'reached_m', 'straight_m', 'walk5', 'line5', 'walk10', 'children_walk5', 'children_line5', 'children_walk10', 'walk_band', 'lat', 'lng']
out = d[cols].copy()
for c in ('walk5', 'line5', 'walk10'): out[c] = (100 * out[c]).round(1)
out = out.rename(columns={'walk5': 'pct_streets_walk5', 'line5': 'pct_streets_line5', 'walk10': 'pct_streets_walk10'})
for c in ('children', 'children_walk5', 'children_line5', 'children_walk10'): out[c] = out[c].round(2)
out.to_csv(T('meshblocks.csv'), index=False)
shade = pg['shade_level'].str.title().value_counts().to_dict()
N = {'date_osm': '22 November 2026', 'date_playgrounds': '28 March 2026 (last update of the ACT dataset)', 'census': '2021',
     'walk_m': 400, 'walk_kmh': 4.8, 'totals': tot, 'prep': prep, 'playgrounds': int(len(pg)), 'playground_kinds': pg['asset_sub_type'].str.title().value_counts().to_dict(), 'shade': shade,
     'engine': {k: {x: v[x] for x in ('points', 'reached', 'network_m', 'covered_m', 'covered_share', 'straight_m', 'straight_share')} | {'within': {x: v['within'][x] for x in v['within'] if x != 'areas'}} for k, v in eng.items()},
     'districts': dis.sort_values('pct_walk5').to_dict('records'),
     'suburbs_low': low.to_dict('records'), 'suburbs_high': high.to_dict('records'), 'suburbs_gap': gap.to_dict('records'), 'suburbs_compared': int(len(big))}
json.dump(N, open(os.path.join(B, 'numbers.json'), 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
print(json.dumps(tot, indent=1)); print(dis[['district', 'children', 'pct_walk5', 'pct_line5']].to_string())
print(low[['suburb', 'children', 'playgrounds', 'pct_walk5', 'pct_line5']].to_string()); print(gap[['suburb', 'children', 'pct_walk5', 'pct_line5', 'gap_pts']].to_string())
