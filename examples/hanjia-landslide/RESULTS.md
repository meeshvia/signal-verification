# Hanjia Landslide — Verification Results

## Event

| Field | Value |
|-------|-------|
| **Event** | Rockslope failure at Hanjia, Pengshui County, Chongqing, China |
| **Date** | July 17, 2026, 9:08 AM local time (01:08 UTC) |
| **Coordinates** | 29.27760°N, 108.16604°E |
| **Casualties** | 51 dead, 10 missing |
| **Cause** | Rockslope failure on banks of Wujiang River, suspected road cutting trigger |
| **Sources** | [Reuters](https://www.reuters.com/world/asia-pacific/southwest-china-landslide-leaves-51-dead-10-missing-2026-07-30/), [EOS Landslide Blog](https://eos.org/thelandslideblog/17-july-2026-landslide-at-hanjia-1) |

## Satellite Imagery Timeline

The workflow discovered 5 Sentinel-2 L2A scenes with 100% AOI coverage:

| Date | Phase | Cloud cover | Days from event |
|------|-------|-------------|-----------------|
| July 8, 2026 | Before | 38.0% | -9 days |
| July 11, 2026 | Before | 34.9% | -6 days |
| **July 16, 2026** | **Before** | 56.4% | **-1 day (day before)** |
| **July 21, 2026** | **After** | **6.4%** | **+4 days (very clear)** |
| July 26, 2026 | After | 34.4% | +9 days |

## Verdict

| Field | Value |
|-------|-------|
| **Verdict** | `change_detected` |
| **Confidence** | `high` |
| **Total changed pixels** | 1,595,341 |
| **Total changed area** | 156.2 km² |
| **SAR scenes** | 0 (none available — graceful optical-only fallback) |

## Spectral Index Results

| Index | What it measures | Before mean | After mean | Change | Changed area |
|-------|-----------------|-------------|------------|--------|-------------|
| **NDWI** | Water bodies | -0.239 | -0.410 | -0.171 | 40.8 km² |
| **MNDWI** | Water in terrain | -0.134 | -0.262 | -0.128 | 35.1 km² |
| **BSI** | Bare soil exposure | -0.090 | -0.124 | -0.035 | 4.5 km² |
| **NDMI** | Vegetation moisture | +0.116 | +0.172 | +0.056 | 9.3 km² |
| **NDVI** | Vegetation density | +0.287 | +0.469 | +0.181 | 41.0 km² |
| **NBR** | Vegetation moisture/burn | +0.253 | +0.333 | +0.080 | 25.5 km² |

## What the Imagery Shows

### Natural color animation (GIF)
The 5-frame animation cycles through July 8 → July 11 → July 16 (before) → July 21 → July 26 (after).

- **Pre-event frames (July 8–16):** The Wujiang River valley appears stable with vegetated slopes.
- **Post-event frame (July 21, 6% cloud):** A prominent **light-brown landslide scar** is visible on the west bank of the river, just south of a major bend. The river water downstream appears significantly **muddier and browner** compared to pre-event frames — consistent with debris entering the river.
- **Post-event frame (July 26):** The scar and turbid river water remain visible.

### Spectral index change maps
- **NDVI change:** A linear feature of vegetation loss runs through the center of the AOI, consistent with the rockslope failure path stripping vegetation from the slope.
- **NDWI/MNDWI change:** Water index decreased sharply in areas surrounding the river, while the river channel itself shows changes consistent with altered water quality and flow.
- **BSI change:** Localized areas of increased bare soil exposure are visible, though the landslide scar itself is relatively small compared to the full AOI.

## How to Reproduce

```bash
export TILEBOX_API_KEY="your-key-here"

signal-verification-submit \
  --aoi examples/hanjia-landslide/aoi.geojson \
  --event-date 2026-07-17 \
  --title "Hanjia landslide — Pengshui County" \
  --description "Rockslope failure on Wujiang River, 51 dead, 10 missing" \
  --search-start 2026-06-01 \
  --search-end 2026-07-31 \
  --min-coverage 0.1 \
  --before-count 3 \
  --after-count 2
```

Outputs appear in `~/signal-verification-outputs/hanjia-landslide-pengshui-county/`.

## Credential Requirements

Only one: `TILEBOX_API_KEY`. No AWS, Copernicus, Microsoft, or Element 84
credentials needed. Scene discovery and asset resolution go entirely through
Tilebox datasets. Imagery is read from public cloud-optimized GeoTIFFs.
