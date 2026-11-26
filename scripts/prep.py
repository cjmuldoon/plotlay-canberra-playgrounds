# Prepare the Canberra playgrounds tables from the raw downloads (run with python3 -I from the build folder).
# In:  raw/act/playgrounds.geojson (ACT Government, CC BY 4.0), raw/abs/mb_*.geojson (ASGS 2021 mesh blocks, CC BY 4.0),
#      raw/abs/mbcounts.xlsx (2021 Census mesh block counts), raw/abs/gcp/.../2021Census_G04A_ACT_SA1.csv (age by SA1),
#      raw/abs/au_asgs3_sal.fgb (ABS suburbs and localities 2021).
# Out: tables/meshblocks.geojson (Canberra's mesh blocks with people, estimated children 0 to 14 and suburb),
#      tables/playgrounds.geojson (the 537 playgrounds as points, with the attributes kept), tables/prep.json
import json, os, sys, glob
import openpyxl, pandas as pd, geopandas as gpd
from shapely.geometry import shape, mapping

B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(B, 'raw')
os.makedirs(os.path.join(B, 'tables'), exist_ok=True)

# mesh blocks
feats = []
for f in sorted(glob.glob(os.path.join(R, 'abs', 'mb_*.geojson'))):
    feats += json.load(open(f))['features']
mb = gpd.GeoDataFrame.from_features(feats, crs=4326)
mb = mb[~mb['sa3_name_2021'].isin(['Uriarra - Namadgi', 'Migratory - Offshore - Shipping (ACT)', 'No usual address (ACT)'])].copy()

# counts (Table 8 is the ACT)
wb = openpyxl.load_workbook(os.path.join(R, 'abs', 'mbcounts.xlsx'), read_only=True)
rows = []
for s in wb.sheetnames:
    if not s.startswith('Table'):
        continue
    for r in wb[s].iter_rows(values_only=True):
        if r and isinstance(r[0], str) and r[0].startswith('8') and len(r[0]) == 11 and r[5] == 8:
            rows.append({'mb_code_2021': r[0], 'dwellings': int(r[3] or 0), 'persons': int(r[4] or 0)})
cnt = pd.DataFrame(rows)
mb = mb.merge(cnt, on='mb_code_2021', how='left').fillna({'dwellings': 0, 'persons': 0})

# children 0 to 14 by SA1, spread to each mesh block by its share of the SA1's people
g04 = pd.read_csv(glob.glob(os.path.join(R, 'abs', 'gcp', '*', '2021Census_G04A_ACT_SA1.csv'))[0], dtype={'SA1_CODE_2021': str})
g04['kids'] = g04['Age_yr_0_4_P'] + g04['Age_yr_5_9_P'] + g04['Age_yr_10_14_P']
g04['sa1_people'] = g04['Tot_P'] if 'Tot_P' in g04 else None
if g04['sa1_people'].isna().all():
    b = pd.read_csv(glob.glob(os.path.join(R, 'abs', 'gcp', '*', '2021Census_G04B_ACT_SA1.csv'))[0], dtype={'SA1_CODE_2021': str})
    g04 = g04.merge(b[['SA1_CODE_2021', 'Tot_P']], on='SA1_CODE_2021'); g04['sa1_people'] = g04['Tot_P']
sa1 = g04[['SA1_CODE_2021', 'kids', 'sa1_people']].rename(columns={'SA1_CODE_2021': 'sa1_code_2021'})
mb = mb.merge(sa1, on='sa1_code_2021', how='left')
mbp = mb.groupby('sa1_code_2021')['persons'].transform('sum')
mb['children'] = (mb['kids'] * mb['persons'] / mbp.where(mbp > 0)).fillna(0)

# suburb of each mesh block: the SAL its inside point falls in
sal = gpd.read_file(os.path.join(B, 'raw', 'abs', 'au_asgs3_sal.fgb'), bbox=(148.7, -35.95, 149.45, -35.1)).to_crs(4326)
sal = sal[sal['state'] == 'ACT'][['name', 'geometry']]
namecol = 'name'
pts = mb.copy(); pts['geometry'] = mb.representative_point()
j = gpd.sjoin(pts[['mb_code_2021', 'geometry']], sal[[namecol, 'geometry']], how='left', predicate='within').drop_duplicates('mb_code_2021')
mb = mb.merge(j[['mb_code_2021', namecol]].rename(columns={namecol: 'suburb'}), on='mb_code_2021', how='left')
mb['suburb'] = mb['suburb'].fillna('').str.replace(r' \(ACT\)$', '', regex=True)

# only mesh blocks where people live go in the layer (the rest change no count)
live = mb[mb['persons'] > 0].copy()
# rural and edge blocks over 1 km² (farms, the urban edge) are left out: they hold few children and would stretch the
# street network fetched across empty country
live['km2'] = live.to_crs(3577).area / 1e6
left_out = live[live['km2'] > 1]
live = live[live['km2'] <= 1].copy()
live['children'] = live['children'].round(2)
live['geometry'] = live.geometry.simplify(0.00001, preserve_topology=True)
out = live[['mb_code_2021', 'mb_category_2021', 'sa1_code_2021', 'sa2_name_2021', 'sa3_name_2021', 'suburb', 'dwellings', 'persons', 'children', 'geometry']]
out = out.rename(columns={'mb_code_2021': 'mb', 'mb_category_2021': 'category', 'sa1_code_2021': 'sa1', 'sa2_name_2021': 'sa2', 'sa3_name_2021': 'district'})
out.to_file(os.path.join(B, 'tables', 'meshblocks.geojson'), driver='GeoJSON', COORDINATE_PRECISION=6)

# playgrounds: a point inside each outline
pg = gpd.read_file(os.path.join(R, 'act', 'playgrounds.geojson'))
pg['geometry'] = pg.geometry.representative_point()
keep = ['ASSET_ID', 'ASSET_NAME', 'LOCATION', 'ASSET_SUB_TYPE', 'CATEGORY', 'SHADE_LEVEL', 'SHADE_DESCRIPTION', 'SUBURB', 'SURFACE_AREA', 'geometry']
pg = pg[keep].rename(columns={k: k.lower() for k in keep if k != 'geometry'})
pg['surface_area'] = pg['surface_area'].round(1)
pg.to_file(os.path.join(B, 'tables', 'playgrounds.geojson'), driver='GeoJSON', COORDINATE_PRECISION=6)

info = {'meshblocks_all': int(len(mb)), 'meshblocks_with_people': int(len(live)), 'persons': int(live['persons'].sum()), 'children': round(float(live['children'].sum())),
        'left_out_blocks': int(len(left_out)), 'left_out_children': round(float(left_out['children'].sum())), 'left_out_persons': int(left_out['persons'].sum()),
        'children_sa1_total': int(sa1[sa1['sa1_code_2021'].isin(mb['sa1_code_2021'])]['kids'].sum()), 'playgrounds': int(len(pg)), 'suburbs': int(live['suburb'].nunique()),
        'bbox': [round(x, 5) for x in live.total_bounds]}
json.dump(info, open(os.path.join(B, 'tables', 'prep.json'), 'w'), indent=1)
print(info)
