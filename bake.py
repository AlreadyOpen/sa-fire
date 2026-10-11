"""South Australia fire layers, as published plus two tile sets each. Per layer:
  <member>_GDA2020.geojson   the GeoJSON from the source zip, byte for byte (GDA2020, EPSG:7844)
  <member>_GDA94.geojson     the same features in GDA94, also byte for byte (sources that ship one)
  <layer>.pmtiles            LOSSLESS tiles: zooms 4 to 14, every field plus `fid` (the feature's position in the GDA2020 file,
                             from 0). Zooms 4 to 13: no feature or tile size limit, no tiny-polygon reduction, no point
                             thinning (-r1; shapes are
                             simplified). Zoom 14: every feature at full detail, no simplification. The bake fails unless
                             zoom 14 holds every feature (a sliver that collapses on the zoom-14 grid goes in again as a point
                             on its surface, `tiny_polygon_point: true`).
  <layer>-thinned.pmtiles    THINNED tiles: tippecanoe's defaults (500 KB tiles, 200,000 features a tile) plus
                             --drop-densest-as-needed, zooms 4 to 14: features are left out where tiles get dense.
index.json: counts per layer (features in each GeoJSON, features at zoom 14 of each tile set) and `sources` (each zip's URL,
Last-Modified, ETag and size). Checked weekly: when no zip changed since the published index.json, nothing is baked
(REBAKE=1 bakes anyway).
HOLD layers (licence not settled by Helen): baked and published only with HOLD=1, which no workflow sets.
Usage: python3 bake.py [layer ...]   (default: every OPEN layer; with HOLD=1 every layer)"""
import datetime, json, os, re, shutil, subprocess, sys, time, urllib.error, urllib.request, zipfile
import sources

WC, DPTI = 'https://apps.waterconnect.sa.gov.au/GISDownloads/', 'https://www.dptiapps.com.au/dataportal/'
# layer -> (zip URL, Data.SA dataset id, open). open=False: HOLD, never published unless HOLD=1.
LAYERS = {
    'fire-history': (WC + 'FIREMGT_FireHistory_geojson.zip', 'e5434c77-9815-48e6-8ea7-fb35c78f6786', True),
    'last-fire': (WC + 'FIREMGT_LastFire_geojson.zip', 'e81e147c-aba1-4d92-acf3-8cd5163c1104', True),
    'bushfire-management-areas': (DPTI + 'BushfireManagementAreas_geojson.zip', 'd93dc636-ec20-45f2-beb0-998b1c5f438c', True),
    'emergency-location-markers': (WC + 'TOPO_EmergencyLocationMarkers_geojson.zip', '52e3d746-c8d1-407f-8561-d2afcd5f6ef5', True),
    'prescribed-burns': (WC + 'Upcoming_Prescribed_Burns_geojson.zip', '13d3bb89-4354-4a36-9857-b8ee7ad93904', False),     # CC BY-ND
    'fire-ban-districts': (DPTI + 'FireBanDistricts_geojson.zip', 'ec5b0373-63a2-4193-b095-2dd5b66edf3f', False),        # catalogue CC BY-NC-ND
    'bushfire-safer-places': (DPTI + 'BushfireSaferPlaces_geojson.zip', '00ccaac9-d75a-45ad-a6b2-8a9d70d46aa3', False),
    'last-resort-refuges': (DPTI + 'BushfireLastResortRefuges_geojson.zip', '4caf5333-138e-4048-b71f-15c59163355a', False),
    'bmap-asset-points': (DPTI + 'BMAPAssetPoints_geojson.zip', '1897bf91-5221-4719-bce2-341721a85d51', False),
    'bmap-asset-lines': (DPTI + 'BMAPAssetLines_geojson.zip', '1897bf91-5221-4719-bce2-341721a85d51', False),
    'bmap-asset-polygons': (DPTI + 'BMAPAssetPolygons_geojson.zip', '1897bf91-5221-4719-bce2-341721a85d51', False),
}
HOLD = os.environ.get('HOLD') == '1'
OPEN = [l for l, v in LAYERS.items() if v[2]]
UA = {'User-Agent': 'AlreadyOpen sa-fire (https://github.com/AlreadyOpen/sa-fire)'}
REPO = 'alreadyopen/sa-fire'
MINZOOM, MAXZOOM = 4, 14


def retry(f, tries=4):
    for i in range(tries):
        try: return f()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if isinstance(e, urllib.error.HTTPError) and e.code < 500 or i == tries - 1: raise
            print(f'::warning::{e}; retrying in {60 << i} s', flush=True); time.sleep(60 << i)


def head(layer):
    u = LAYERS[layer][0]
    def get():
        with urllib.request.urlopen(urllib.request.Request(u, method='HEAD', headers=UA), timeout=120) as r:
            return {'url': u, 'last_modified': r.headers['Last-Modified'], 'etag': r.headers.get('ETag'), 'bytes': int(r.headers['Content-Length'])}
    return retry(get)


def published():
    try: return json.load(urllib.request.urlopen(f'https://huggingface.co/buckets/{REPO}/resolve/index.json', timeout=60))
    except urllib.error.HTTPError as e:
        if e.code in (401, 404): return None
        raise


def download(layer, src):
    p = os.path.join(sources.CACHE, os.path.basename(src['url'])); meta = p + '.json'
    if os.path.exists(meta) and json.load(open(meta)) == src and os.path.getsize(p) == src['bytes']:
        return p
    def get():
        with urllib.request.urlopen(urllib.request.Request(src['url'], headers=UA), timeout=1800) as r, open(p + '.part', 'wb') as f:
            shutil.copyfileobj(r, f, 1 << 24)
    retry(get)
    assert os.path.getsize(p + '.part') == src['bytes'], f'{layer}: short download'
    os.replace(p + '.part', p); json.dump(src, open(meta, 'w'))
    return p


def fids(pmtiles, layer, zoom=MAXZOOM):
    """the distinct `fid` values at one zoom (a feature crossing tiles appears in each); decoded as a stream"""
    ids, pat = set(), re.compile(r'"fid": ?(\d+)')
    with subprocess.Popen(['tippecanoe-decode', '-l', layer, '-z', str(zoom), '-Z', str(zoom), pmtiles], stdout=subprocess.PIPE, text=True) as p:
        for line in p.stdout:
            if '"Feature"' in line and (m := pat.search(line)): ids.add(int(m.group(1)))
    assert p.returncode == 0, f'tippecanoe-decode failed on {pmtiles}'
    return ids


def bake(con, layer, z, tmp):
    o = lambda f: os.path.join(sources.OUT, f)
    names = zipfile.ZipFile(z).namelist()
    g20 = [n for n in names if n.endswith('_GDA2020.geojson')]
    assert len(g20) == 1, f'{layer}: expected one *_GDA2020.geojson in the zip, found {g20}'
    files, counts = [], {}
    for n in [n for n in names if re.search(r'_GDA(2020|94)\.geojson$', n)]:      # published unchanged, byte for byte
        with zipfile.ZipFile(z).open(n) as src, open(o(n), 'wb') as dst: shutil.copyfileobj(src, dst, 1 << 24)
        files.append(n)
        counts[f'{layer}_{"gda2020" if n in g20 else "gda94"}'] = len(json.load(open(o(n), encoding='utf-8-sig'))['features'])
    fs = json.load(open(o(g20[0]), encoding='utf-8-sig'))['features']; rows = len(fs)
    assert all(f.get('geometry') for f in fs), f'{layer}: features without geometry'
    assert not any({'fid', 'tiny_polygon_point'} & (f.get('properties') or {}).keys() for f in fs), f'{layer}: has its own fid or tiny_polygon_point field'
    gl, pl = os.path.join(tmp, layer + '.geojsonl'), os.path.join(tmp, layer + '-points.geojsonl')
    lo, hi, pt = (os.path.join(tmp, f'{layer}-{x}.pmtiles') for x in ('lo', 'hi', 'pt'))
    with open(gl, 'w') as w:                                                       # fid = position in the GDA2020 file
        for i, f in enumerate(fs): w.write(json.dumps({**f, 'properties': {**(f.get('properties') or {}), 'fid': i}}) + '\n')
    del fs
    common = ['tippecanoe', '--force', '--quiet', '-l', layer, '-t', tmp, '--read-parallel']
    nolimit = ['--no-feature-limit', '--no-tile-size-limit', '--no-tiny-polygon-reduction', '-r1']   # -r1: no point thinning by zoom either
    deep = [f'-Z{MAXZOOM}', f'-z{MAXZOOM}', *nolimit, '--no-line-simplification']
    # lossless: every feature at every zoom tippecanoe can draw it at, full detail at zoom 14
    subprocess.run(common + ['-o', lo, f'-Z{MINZOOM}', f'-z{MAXZOOM - 1}', *nolimit, gl], check=True)
    subprocess.run(common + ['-o', hi] + deep + [gl], check=True)
    seen = fids(hi, layer)
    gone = set(range(rows)) - seen; missing = len(gone)
    parts = [lo, hi]
    if missing:   # line i of gl is fid i. Not through GDAL: it renames `fid` to fid_1 where the source has its own `FID` field
        with open(gl) as r, open(pl, 'w') as w:
            for i, line in enumerate(r):
                if i in gone:
                    f = json.loads(line)
                    g = con.execute('SELECT ST_AsGeoJSON(ST_PointOnSurface(ST_GeomFromGeoJSON(?)))', [json.dumps(f['geometry'])]).fetchone()[0]
                    w.write(json.dumps({**f, 'geometry': json.loads(g), 'properties': {**f['properties'], 'tiny_polygon_point': True}}) + '\n')
        subprocess.run(common + ['-o', pt] + deep + [pl], check=True)
        assert len(fids(pt, layer)) == missing, f'{layer}: points for collapsed slivers missing at zoom {MAXZOOM}'
        parts.append(pt)
    subprocess.run(['tile-join', '--force', '--quiet', '--no-tile-size-limit', '-o', o(layer + '.pmtiles')] + parts, check=True)
    n = len(seen) + missing
    assert n == rows, f'{layer}: {n} features at zoom {MAXZOOM}, {rows} in the source'
    # thinned: tippecanoe's defaults plus --drop-densest-as-needed (counted, not asserted: leaving features out is the point)
    subprocess.run(common + ['-o', o(layer + '-thinned.pmtiles'), f'-Z{MINZOOM}', f'-z{MAXZOOM}', '--drop-densest-as-needed', gl], check=True)
    counts |= {f'{layer}_tiles_deepest_zoom': n, f'{layer}_tiny_polygon_points': missing, f'{layer}_tiles_minzoom': len(fids(o(layer + '.pmtiles'), layer, MINZOOM)),
               f'{layer}_thinned_deepest_zoom': len(fids(o(layer + '-thinned.pmtiles'), layer)),
               f'{layer}_thinned_minzoom': len(fids(o(layer + '-thinned.pmtiles'), layer, MINZOOM))}
    for f in [gl, pl] + parts:
        if os.path.exists(f): os.remove(f)
    return files, counts


def main():
    allowed = list(LAYERS) if HOLD else OPEN
    want = sys.argv[1:] or allowed
    assert set(want) <= set(allowed), f'unknown or HOLD layer (HOLD=1 to bake those): {set(want) - set(allowed)}'
    for d in (sources.CACHE, sources.OUT): os.makedirs(d, exist_ok=True)
    srcs = {l: head(l) for l in want}
    old = published()
    if old and os.environ.get('REBAKE') != '1' and set(old.get('layers', [])) == set(want) and all(old['sources'].get(l) == srcs[l] for l in want):
        print(json.dumps({'unchanged': True, 'since': old['built']})); return        # no index.json: publish.py does nothing
    import duckdb                                                    # here, so check.py and publish.py can import LAYERS without it
    tmp = os.path.join(sources.DATA, 'tmp'); os.makedirs(tmp, exist_ok=True)
    con = duckdb.connect(os.path.join(tmp, 'bake.duckdb')); con.execute('INSTALL spatial; LOAD spatial')
    counts, files = {}, {}
    for l in want:
        t = datetime.datetime.now()
        files[l], c = bake(con, l, download(l, srcs[l]), tmp)
        counts |= c
        print(json.dumps({'layer': l, 'seconds': (datetime.datetime.now() - t).seconds, **c,
                          **{f: os.path.getsize(os.path.join(sources.OUT, f)) for f in files[l] + [l + '.pmtiles', l + '-thinned.pmtiles']}}), flush=True)
    con.close(); shutil.rmtree(tmp)
    idx = {'built': datetime.datetime.now().isoformat(timespec='seconds'), 'counts': counts, 'layers': want, 'geojson': files,
           'hold': [l for l in want if not LAYERS[l][2]], 'sources': srcs, 'crs': 'EPSG:7844 (GDA2020); the *_GDA94.geojson files are EPSG:4283'}
    json.dump(idx, open(os.path.join(sources.OUT, 'index.json'), 'w'), indent=1)
    print(json.dumps(idx))


if __name__ == '__main__':
    main()
