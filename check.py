"""Data-free checks for CI on every push (no downloads, no token): every script compiles, sources.json declares each source with
its licence and owner and matches bake.LAYERS, the card credits every published owner, HOLD layers stay unpublished (no workflow
sets HOLD), every workflow parses as YAML with its triggers, and the publish gate's self-test passes.
Usage: python3 check.py"""
import glob, json, py_compile, re, subprocess, sys
import yaml
import bake

for p in glob.glob('*.py'): py_compile.compile(p, doraise=True)
src = json.load(open('sources.json')); card = open('hf/README.md', encoding='utf-8').read()
assert {s['layer']: s['published'] for s in src} == {l: v[2] for l, v in bake.LAYERS.items()}, 'sources.json and bake.LAYERS disagree'
for s in src:
    missing = {'name', 'owner', 'url', 'licence'} - s.keys()
    assert not missing, f'{s.get("name")}: missing {missing}'
    assert s['url'].startswith('https://') and s['licence'].startswith('https://'), f'{s["name"]}: url and licence must be https links'
    if s['published']: assert s['owner'] in card, f'hf/README.md does not credit {s["owner"]}'
assert re.search(r'^license_link: https://', card, re.M), 'hf/README.md has no license_link'
for w in glob.glob('.github/workflows/*.yml'):
    t = open(w).read(); y = yaml.safe_load(t)                          # YAML reads the key `on` as True
    assert isinstance(y, dict) and (y.get('on') or y.get(True)) and y.get('jobs'), f'{w}: no triggers or jobs (invalid workflow)'
    assert not re.search(r'\bHOLD\s*[:=]', t), f'{w}: sets HOLD (HOLD layers must not be published from CI)'
subprocess.run([sys.executable, 'manifest.py'], check=True)
print(f'check: ok ({len(src)} sources, {sum(s["published"] for s in src)} published)')
