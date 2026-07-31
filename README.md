# Signal Verification

A credential-free Tilebox workflow that verifies ground events — landslides,
floods, land clearing, vegetation loss — using Sentinel-2 optical imagery and
Sentinel-1 SAR backscatter change detection.

## Prerequisites

1. **Install the Tilebox CLI** — see [tilebox.com/hello-agent](https://tilebox.com/hello-agent)
2. **Set your Tilebox API key**:
   ```bash
   export TILEBOX_API_KEY="your-key-here"
   ```

That's it. No AWS, Copernicus, Microsoft, or Element 84 credentials needed.
Scene discovery and asset resolution go entirely through Tilebox datasets.
Imagery is read from public cloud-optimized GeoTIFFs.

## Quick start

```bash
# Clone and install
git clone https://github.com/meeshvia/signal-verification.git
cd signal-verification
uv sync --extra dev

# Submit a verification job
uv run signal-verification-submit \
  --aoi examples/landslide/aoi.geojson \
  --event-date 2025-07-15 \
  --title "Landslide verification — Cameroon Far North" \
  --description "Verify reported landslide event"

# Run the workflow locally
tilebox workflow run signal-verification
```

## How it works

### Scene discovery (Tilebox only)

The workflow queries two Tilebox datasets using a single `TILEBOX_API_KEY`:

| Sensor | Tilebox dataset | Collection | Credential |
|--------|----------------|------------|------------|
| Sentinel-2 L2A (optical) | `open_data.aws_earth.sentinel2` | `L2A` | `TILEBOX_API_KEY` only |
| Sentinel-1 RTC (SAR) | `tilebox.microsoft_planetary_computer_sentinel1_rtc` | `S1A_IW_RTC` | `TILEBOX_API_KEY` only |

Asset URLs (public COG GeoTIFFs on AWS S3 and Azure Blob Storage) are extracted
from the Tilebox protobuf response — no external API calls.

### Spectral indices (Sentinel-2)

All indices use Sentinel-2 L2A bands available credential-free:

| Index | What it detects | Formula |
|-------|----------------|---------|
| **NDWI** | Water bodies — flooding, drainage | (Green - NIR) / (Green + NIR) |
| **MNDWI** | Water in shadowed/built-up terrain | (Green - SWIR1) / (Green + SWIR1) |
| **BSI** | Bare soil exposure — landslide scars, land clearing | ((SWIR1+Red) - (NIR+Blue)) / ((SWIR1+Red) + (NIR+Blue)) |
| **NDMI** | Vegetation moisture content — drought stress | (NIR - SWIR1) / (NIR + SWIR1) |
| **NDVI** | Vegetation density — deforestation, crop loss | (NIR - Red) / (NIR + Red) |
| **NBR** | Vegetation moisture/burn change | (NIR - SWIR2) / (NIR + SWIR2) |

### SAR backscatter change (Sentinel-1)

SAR sees through clouds and works at night — critical for landslide
verification during rainy season when optical imagery is often cloud-obscured.
The workflow computes VV and VH backscatter difference in dB between the
closest before/after acquisitions.

### Output

By default, outputs are written to `~/signal-verification-outputs/<slug>/`.
If you pass `--output-dir` with an absolute path, outputs go there instead.

```
~/signal-verification-outputs/<slug>/
├── verification-report.json    # Structured analysis with per-index statistics
├── optical-natural-color.gif   # Before/after animation
├── optical-contact-sheet.png   # All scenes side by side
├── index-maps/                 # Individual spectral index maps
│   ├── ndwi-before.png
│   ├── ndwi-change.png
│   ├── mndwi-before.png
│   ├── mndwi-change.png
│   ├── bsi-before.png
│   ├── bsi-change.png
│   └── ...
├── sar-vv-change.png           # SAR VV backscatter change map
└── sar-vh-change.png           # SAR VH backscatter change map
```

> **Finding your outputs**: when a job runs via a deployed release runner,
> relative paths resolve to the runner's release cache directory. The default
> `~/signal-verification-outputs/` ensures outputs are always in a predictable
> location. The job logs also print the absolute `output_dir` path when the
> task completes.

### JSON verification report

The `verification-report.json` contains:

- Event metadata (title, date, description, AOI)
- Search parameters and scene inventory
- Per-index change statistics (before mean, after mean, change mean, changed pixel count, changed area in km²)
- SAR backscatter change statistics (mean dB change, max increase/decrease, changed area)
- Overall verdict: `change_detected`, `possible_change`, or `no_significant_change`
- Confidence level: `high`, `medium`, or `low`

## Options

```
--indices ndwi,mndwi,bsi,ndmi,ndvi,nbr   # Comma-separated; choose which to compute
--no-sar                                  # Skip Sentinel-1 SAR analysis
--before-count 3                          # Number of before-event scenes
--after-count 3                           # Number of after-event scenes
--max-cloud-cover 60                      # Max cloud cover % for optical scenes
--search-start 2025-06-01                 # Custom search start (defaults to 45 days before event)
--search-end 2025-08-31                   # Custom search end (defaults to 45 days after event)
--output-dir /path/to/outputs             # Absolute path for outputs (defaults to ~/signal-verification-outputs)
```

## Development

```bash
uv sync --extra dev
uv run pytest -v
```

## License

MIT
