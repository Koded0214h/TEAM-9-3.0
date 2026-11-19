# Ikeja LGA demonstration data

This directory contains a small, reproducible dataset for the Repelect MVP.

## Scope

- State: Lagos (INEC state ID 25)
- LGA: Ikeja (INEC LGA code 11, internal ID 516)
- Wards/registration areas: all 10 Ikeja wards
- Polling units: 667 total
- Usable INEC locator coordinates: 642
- Deterministic ward-centroid coordinate estimates: 25 records whose locator GPS values were null

## Provenance and limitations

Polling-unit IDs, codes, names, hierarchy, and coordinates were retrieved from the public INEC CVR polling-unit locator through the archived extraction in `kcemenike/find-my-polling-unit`. The repository documents the exact INEC endpoints and preserves coordinates keyed by INEC internal polling-unit ID.

- Official locator: https://cvr.inecnigeria.org/pu
- Extraction source: https://github.com/kcemenike/find-my-polling-unit/tree/main/inec_scraped
- Extraction files: `state_25_lagos.json` and `state_25_lagos_coords.json`
- Retrieved for this demo: 19 November 2026

INEC describes locator directions as approximate. These coordinates must be verified before operational use. The CSV `coordinate_source` column distinguishes `inec_locator` values from `estimated_ward_centroid` fallbacks; estimated coordinates must not be presented as INEC GPS data.

The polling-unit names are location descriptions, not verified postal addresses. The `address` column appends ward/LGA/state context for display and search.

INEC voter counts were not present in the locator response. The `registered_voters` values in this demo are deterministic **synthetic values** created only to exercise capacity analysis, equipment rules, and engine contracts. They must never be represented as official registration figures.

The administrative polygons are synthetic rectangular demo extents derived separately from each ward's polling-unit coordinate range. They are suitable only for demonstrating containment validation and must not be used as legal or administrative boundaries.

When importing these files, create both dataset records with classification `sample` or `synthetic` as follows:

- `administrative_geography.geojson`: `synthetic`
- `polling_units.csv`: `sample` (with synthetic voter-count metadata noted)
