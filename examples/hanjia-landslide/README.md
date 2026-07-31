# Hanjia landslide — Pengshui County, Chongqing, China

On 17 July 2026 at 9:08 AM local time (01:08 UTC), a large rockslope failure
occurred on the banks of the Wujiang River at Hanjia, Pengshui Miao and Tujia
Autonomous County, Chongqing, China. The landslide buried over 10 residential
buildings, killing 51 people with 10 still missing.

**Event coordinates:** 29.27760N, 108.16604E

**Source:** [Reuters](https://www.reuters.com/world/asia-pacific/southwest-china-landslide-leaves-51-dead-10-missing-2026-07-30/),
[EOS Landslide Blog](https://eos.org/thelandslideblog/17-july-2026-landslide-at-hanjia-1)

## Run

```bash
# Set your Tilebox API key
export TILEBOX_API_KEY="your-key-here"

# Submit the verification job (optical + SAR)
signal-verification-submit \
  --aoi aoi.geojson \
  --event-date 2026-07-17 \
  --title "Hanjia landslide — Pengshui County" \
  --description "Rockslope failure on Wujiang River, 51 dead, 10 missing" \
  --search-start 2026-06-01 \
  --search-end 2026-07-31 \
  --min-coverage 0.1 \
  --before-count 3 \
  --after-count 3
```

## Why SAR matters here

Pengshui County is in mountainous terrain during monsoon season (July).
Optical imagery is frequently cloud-obscured. Sentinel-1 SAR sees through
clouds and can detect surface change regardless of weather conditions.

## Output

Check ~/signal-verification-outputs/hanjia-landslide-pengshui-county/ for:
- verification-report.json — structured analysis with verdict and statistics
- optical-natural-color.gif — before/after animation
- optical-contact-sheet.png — all scenes side by side
- index-maps/ — spectral index maps (NDWI, MNDWI, BSI, NDMI, NDVI, NBR)
- sar-vv-change.png / sar-vh-change.png — SAR backscatter change maps
