---
pretty_name: South Australia fire layers
license: cc-by-4.0
license_link: https://creativecommons.org/licenses/by/4.0/
tags:
  - geospatial
  - bushfire
  - fire-history
  - emergency
  - south-australia
---

# South Australia fire layers

Statewide fire layers published on Data.SA by the Department for Environment and Water and the SA Country Fire Service, as the
GeoJSON files exactly as published plus two sets of vector tiles, checked weekly and rebuilt when a source changes by
[AlreadyOpen/sa-fire](https://github.com/AlreadyOpen/sa-fire). Every feature and every field of each source is kept.

| Layer | Source | Holds |
|---|---|---|
| `fire-history` | [Bushfires and Prescribed Burns History](https://data.sa.gov.au/data/dataset/e5434c77-9815-48e6-8ea7-fb35c78f6786) (Department for Environment and Water) | Every mapped bushfire and prescribed burn on record (`INCIDENTTY`, `FIREDATE`, `FIREYEAR`, `HECTARES`) |
| `last-fire` | [Last Bushfire and Prescribed Burn Boundaries](https://data.sa.gov.au/data/dataset/e81e147c-aba1-4d92-acf3-8cd5163c1104) (Department for Environment and Water) | The most recent fire at each place: the time since fire |
| `bushfire-management-areas` | [Bushfire Management Areas](https://data.sa.gov.au/data/dataset/d93dc636-ec20-45f2-beb0-998b1c5f438c) (SA Country Fire Service) | The nine bushfire management areas |
| `emergency-location-markers` | [Emergency Location Markers](https://data.sa.gov.au/data/dataset/52e3d746-c8d1-407f-8561-d2afcd5f6ef5) (Department for Environment and Water) | Numbered markers on trails and parks to tell emergency services where you are |

Per layer:

- **`*_GDA2020.geojson`** and **`*_GDA94.geojson`** (in this dataset; the GDA2020 file also on the
  [bucket](https://huggingface.co/buckets/alreadyopen/sa-fire)): the source's GeoJSON files, byte for byte, with their
  original names. GDA2020 is EPSG:7844, which web maps can use as WGS 84 (they differ by under 2 m); GDA94 is EPSG:4283.
- **`<layer>.pmtiles`** (bucket, read by browsers), **lossless**: zooms 4 to 14, every field plus `fid` (the feature's
  position in the GDA2020 file, from 0). No feature or tile size limit and no tiny-polygon reduction at any zoom; shapes are
  simplified below zoom 14. **Zoom 14 holds every feature** at full detail (the bake fails otherwise); a polygon too thin to
  survive the zoom-14 grid is also given as a point on its surface, with `tiny_polygon_point: true`.
- **`<layer>-thinned.pmtiles`** (bucket), **thinned**: tippecanoe's defaults plus `--drop-densest-as-needed`, zooms 4 to 14.
  Features are left out where tiles get dense, so lower zooms show fewer of them. `index.json` counts what each zoom keeps.

`index.json` holds the counts (features in each GeoJSON; features at zoom 4 and 14 of each tile set), each source's URL,
Last-Modified, ETag and size. `manifest.json` lists every file's sha256. Built with tippecanoe 2.79.0.

## Sources and terms

Data from the Department for Environment and Water, Government of South Australia, and the SA Country Fire Service, Government of South Australia, published
on [Data.SA](https://data.sa.gov.au) under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)
(the licence note in the Bushfire Management Areas zip, dated 2015, names CC BY 3.0 Australia). Changes: the tiles are a
conversion of the GeoJSON; the GeoJSON files are unchanged; nothing removed. Provided as is, with no warranty, not endorsed by
the Government of South Australia. Not a warning service: for fires now, go to the [CFS](https://www.cfs.sa.gov.au/).
