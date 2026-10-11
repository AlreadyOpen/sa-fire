# sa-fire

South Australia fire layers from Data.SA, CC BY 4.0: Bushfires and Prescribed Burns History, Last Bushfire and Prescribed
Burn Boundaries and Emergency Location Markers (Department for Environment and Water), and Bushfire Management Areas (SA
Country Fire Service). For each: the published GeoJSON files unchanged (GDA2020 and GDA94), lossless PMTiles (every feature
at zoom 14, asserted) and thinned PMTiles (tippecanoe defaults, `--drop-densest-as-needed`). Checked weekly and rebuilt when
a source changes; published to Hugging Face ([dataset](https://huggingface.co/datasets/alreadyopen/sa-fire),
[bucket](https://huggingface.co/buckets/alreadyopen/sa-fire) for what browsers read) and mirrored to
[Kaggle](https://www.kaggle.com/datasets/helenkwok/sa-fire). Built from
[pipeline-template](https://github.com/AlreadyOpen/pipeline-template), like
[sa-planning](https://github.com/AlreadyOpen/sa-planning).

    python3 bake.py [layer ...]   # data/out/: GeoJSON + PMTiles + index.json (needs tippecanoe 2.79); REBAKE=1 bakes unchanged sources
    python3 publish.py            # gate, then Hugging Face (HF_TOKEN)
    python3 check.py              # data-free checks (CI)

**HOLD layers.** The code also knows Prescribed Burns (CC BY-ND) and the CFS Fire Ban Districts, Bushfire Safer Places, Last
Resort Refuges and BMAP Assets (Data.SA catalogue: CC BY-NC-ND; the licence note inside each zip: CC BY 3.0 AU). They are not
baked or published unless `HOLD=1`; `publish.py` refuses a bake that holds one, and `check.py` fails if a workflow sets `HOLD`.

Code: Apache-2.0. Data: CC BY 4.0 (Government of South Australia), see `sources.json`.
