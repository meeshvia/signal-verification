# Signal Verification

## Overview
Credential-free Tilebox workflow that verifies ground events (landslides, floods,
land clearing) using Sentinel-2 optical and Sentinel-1 SAR data.

## Build & Test
```bash
uv sync --extra dev
uv run pytest -v
```

## Architecture
- `catalog.py` — Tilebox dataset queries for Sentinel-2 L2A and Sentinel-1 RTC
- `indices.py` — Spectral index computations (NDWI, MNDWI, BSI, NDMI, NDVI, NBR)
- `sar.py` — Sentinel-1 SAR backscatter change detection
- `render.py` — Visual outputs (GIFs, index maps, contact sheets)
- `report.py` — JSON verification report generation
- `tasks.py` — Tilebox workflow task definitions
- `runner.py` — Tilebox workflow runner
- `submit.py` — CLI submission script

## Key constraint
The only credential is `TILEBOX_API_KEY`. All scene discovery and asset
resolution goes through Tilebox datasets. Imagery is read from public
cloud-optimized GeoTIFFs — no AWS, Copernicus, or Microsoft credentials needed.
