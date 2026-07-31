from __future__ import annotations

import argparse
from pathlib import Path

from tilebox.workflows import Client

from .tasks import VerifySignal


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit a signal verification workflow job.")
    parser.add_argument("--aoi", required=True, help="Path to a WGS84 Polygon or MultiPolygon GeoJSON file")
    parser.add_argument("--event-date", required=True, help="ISO date or timestamp of the event to verify")
    parser.add_argument("--description", default="", help="Description of the reported event")
    parser.add_argument("--title", default="Signal verification")
    parser.add_argument("--search-start", default="", help="ISO timestamp; defaults to 45 days before event")
    parser.add_argument("--search-end", default="", help="ISO timestamp; defaults to 45 days after event")
    parser.add_argument("--before-count", type=int, default=3, help="Number of before-event scenes")
    parser.add_argument("--after-count", type=int, default=3, help="Number of after-event scenes")
    parser.add_argument("--max-cloud-cover", type=float, default=60, help="Max cloud cover %% for optical scenes")
    parser.add_argument("--min-coverage", type=float, default=0.90, help="Min AOI coverage for optical scenes")
    parser.add_argument("--width", type=int, default=900, help="Output image width in pixels")
    parser.add_argument("--frame-duration-ms", type=int, default=1100, help="GIF frame duration in milliseconds")
    parser.add_argument(
        "--indices",
        default="ndwi,mndwi,bsi,ndmi,ndvi,nbr",
        help="Comma-separated spectral indices to compute",
    )
    parser.add_argument("--no-sar", action="store_true", help="Skip Sentinel-1 SAR analysis")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--name", default="signal-verification")
    args = parser.parse_args()

    aoi = Path(args.aoi).read_text()
    job = Client().jobs().submit(
        args.name,
        VerifySignal(
            aoi_geojson=aoi,
            event_date=args.event_date,
            description=args.description,
            title=args.title,
            search_start=args.search_start,
            search_end=args.search_end,
            before_count=args.before_count,
            after_count=args.after_count,
            max_cloud_cover=args.max_cloud_cover,
            min_coverage=args.min_coverage,
            width=args.width,
            frame_duration_ms=args.frame_duration_ms,
            indices=args.indices,
            include_sar=not args.no_sar,
            output_dir=args.output_dir,
        ),
    )
    print(job.id)


if __name__ == "__main__":
    main()
