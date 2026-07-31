# Landslide verification example

This example AOI covers a mountainous region in Cameroon's Far North,
an area prone to landslides during the rainy season.

## Run

```bash
# Set your Tilebox API key
export TILEBOX_API_KEY="your-key-here"

# Submit the workflow job
signal-verification-submit \
  --aoi aoi.geojson \
  --event-date 2025-07-15 \
  --title "Landslide verification — Cameroon Far North" \
  --description "Verify reported landslide event"

# Run the workflow locally
tilebox workflow run signal-verification
```

## Output

The workflow produces:
- `verification-report.json` — structured analysis with per-index statistics
- `optical-natural-color.gif` — before/after animation
- `sar-vv-change.png` — SAR backscatter change map
- `index-maps/` — individual spectral index maps (NDWI, MNDWI, BSI, NDMI, NDVI, NBR)
- `contact-sheet.png` — all scenes side by side
