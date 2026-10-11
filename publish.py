"""Publish sources.OUT to Hugging Face (needs HF_TOKEN with write access to the alreadyopen org):
  dataset  REPO  index.json + every published GeoJSON (GDA2020 and GDA94) + manifest.json + the card (hf/README.md), versioned
  bucket   REPO  index.json + each layer's GDA2020 GeoJSON, <layer>.pmtiles and <layer>-thinned.pmtiles + manifest.json,
                 overwritten in place (read by browsers: CORS + HTTP Range)
HOLD layers (bake.LAYERS open=False) are never published unless HOLD=1, which no workflow sets: this refuses to run if one is in
the bake. Nothing is uploaded unless the publish gate passes (manifest.py). Does nothing when bake.py found every source unchanged.
Usage: python3 publish.py     (after bake.py)"""
import json, os, sys
import bake, manifest, sources

REPO = 'alreadyopen/sa-fire'
_idx = os.path.join(sources.OUT, 'index.json')
IDX = json.load(open(_idx)) if os.path.exists(_idx) else {'layers': [], 'geojson': {}}
LAYERS = IDX['layers']
if not bake.HOLD and (held := [l for l in LAYERS if not bake.LAYERS[l][2]]):
    sys.exit(f'publish: HOLD layers in the bake, not publishing: {held}')
GEOJSON = [f for l in LAYERS for f in IDX['geojson'][l]]
DATASET_FILES = ['index.json'] + GEOJSON
BUCKET_FILES = ['index.json'] + [f for f in GEOJSON if f.endswith('_GDA2020.geojson')] + [f'{l}{x}.pmtiles' for l in LAYERS for x in ('', '-thinned')]
KAGGLE = ('helenkwok/sa-fire', 'AlreadyOpen: South Australia fire layers')     # mirrored by kaggle_mirror.py (title 6-50 chars)

def main():
    if not LAYERS:
        print(json.dumps({'nothing new': True})); return
    from huggingface_hub import CommitOperationAdd, HfApi, batch_bucket_files, create_bucket
    o = lambda f: os.path.join(sources.OUT, f)
    m = manifest.manifest(sources.OUT, sorted(set(DATASET_FILES + BUCKET_FILES)), IDX['counts'], IDX['built'])
    manifest.gate(m, f'https://huggingface.co/buckets/{REPO}/resolve/manifest.json')
    json.dump(m, open(o('manifest.json'), 'w'), indent=1)
    api = HfApi(); api.create_repo(REPO, repo_type='dataset', exist_ok=True)
    card = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hf', 'README.md')
    api.create_commit(REPO, repo_type='dataset', commit_message=f"bake of {IDX['built']}",
                      operations=[CommitOperationAdd(f, o(f)) for f in DATASET_FILES + ['manifest.json']] + [CommitOperationAdd('README.md', card)])
    create_bucket(REPO, private=False, exist_ok=True)
    batch_bucket_files(REPO, add=[(o(f), f) for f in BUCKET_FILES] + [(o('manifest.json'), 'manifest.json')])   # the gate reads the bucket's
    print(json.dumps({'dataset': f'https://huggingface.co/datasets/{REPO}', 'bucket': f'https://huggingface.co/buckets/{REPO}', 'built': IDX['built'], 'counts': m['counts']}))

if __name__ == '__main__':
    main()
