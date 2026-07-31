from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

from tilebox.workflows import ExecutionContext, Task

from .catalog import (
    Acquisition,
    group_acquisitions,
    parse_datetime,
    search_sentinel1,
    search_sentinel2,
    select_acquisitions,
)
from .indices import (
    INDEX_BANDS,
    INDEX_CONFIG,
    bsi,
    mndwi,
    nbr,
    ndmi,
    ndvi,
    ndwi,
)
from .render import (
    label_frame,
    output_grid,
    output_slug,
    read_band,
    read_visual,
    save_change_png,
    save_contact_sheet,
    save_gif,
    save_index_png,
    save_index_raster,
    validate_aoi,
)
from .report import build_report, compute_index_stats, compute_sar_stats, save_report
from .sar import sar_backscatter_change

INDEX_FUNCS = {
    "ndwi": lambda b: ndwi(b["green"], b["nir"]),
    "mndwi": lambda b: mndwi(b["green"], b["swir16"]),
    "bsi": lambda b: bsi(b["swir16"], b["red"], b["nir"], b["blue"]),
    "ndmi": lambda b: ndmi(b["nir"], b["swir16"]),
    "ndvi": lambda b: ndvi(b["nir"], b["red"]),
    "nbr": lambda b: nbr(b["nir"], b["swir22"]),
}


class VerifySignal(Task):
    aoi_geojson: str
    event_date: str
    description: str = ""
    title: str = "Signal verification"
    search_start: str = ""
    search_end: str = ""
    before_count: int = 3
    after_count: int = 3
    max_cloud_cover: float = 60.0
    min_coverage: float = 0.90
    width: int = 900
    frame_duration_ms: int = 1100
    indices: str = "ndwi,mndwi,bsi,ndmi,ndvi,nbr"
    include_sar: bool = True
    output_dir: str = "outputs"

    @staticmethod
    def identifier() -> tuple[str, str]:
        return "tilebox.com/signal-verification/VerifySignal", "v1.0"

    def execute(self, context: ExecutionContext) -> None:
        context.current_task.display = f"Verify signal: {self.title}"
        aoi = json.loads(self.aoi_geojson)
        validate_aoi(aoi)
        event_date = parse_datetime(self.event_date)

        start = parse_datetime(self.search_start) if self.search_start else event_date - timedelta(days=45)
        end = parse_datetime(self.search_end) if self.search_end else event_date + timedelta(days=45)
        if not start < event_date < end:
            raise ValueError("search_start < event_date < search_end is required")

        requested_indices = [name.strip() for name in self.indices.split(",") if name.strip()]
        for name in requested_indices:
            if name not in INDEX_FUNCS:
                raise ValueError(f"Unknown index '{name}'. Available: {list(INDEX_FUNCS.keys())}")

        # --- Optical: Sentinel-2 ---
        context.logger.info("Querying Sentinel-2 L2A via Tilebox", start=start.isoformat(), end=end.isoformat())
        s2_items = search_sentinel2(aoi, start, end)
        s2_candidates = group_acquisitions(s2_items, aoi)
        optical_scenes = select_acquisitions(
            s2_candidates, event_date, self.before_count, self.after_count,
            self.max_cloud_cover, self.min_coverage,
        )
        total_optical = len(optical_scenes)
        context.progress("optical-scenes").add(total_optical)

        target_crs, target_transform, output_shape = output_grid(aoi, self.width)
        pixel_area_m2 = abs(target_transform.a * target_transform.e)

        # Natural colour frames for GIF and contact sheet
        natural_frames = []
        for scene in optical_scenes:
            frame = read_visual(scene, target_crs, target_transform, output_shape)
            labelled = label_frame(frame, self.title, scene, "Natural colour (Sentinel-2 RGB)")
            natural_frames.append(labelled)
            context.logger.info(
                "Processed optical scene",
                time=scene.time.isoformat(), phase=scene.phase,
                cloud_cover=scene.cloud_cover, coverage=scene.coverage,
            )
            context.progress("optical-scenes").done(1)

        # --- SAR: Sentinel-1 RTC (graceful fallback) ---
        sar_scenes: list[Acquisition] = []
        sar_natural_frames: list[Any] = []
        if self.include_sar:
            context.logger.info("Querying Sentinel-1 RTC via Tilebox", start=start.isoformat(), end=end.isoformat())
            try:
                s1_items = search_sentinel1(aoi, start, end)
                s1_candidates = group_acquisitions(s1_items, aoi)
                sar_scenes = select_acquisitions(
                    s1_candidates, event_date, self.before_count, self.after_count,
                    max_cloud_cover=100.0, min_coverage=0.1,
                )
                context.logger.info("Found SAR scenes", count=len(sar_scenes))
            except Exception as exc:
                context.logger.warning("SAR query failed — continuing with optical only", error=str(exc))
                sar_scenes = []

        # --- Output directory ---
        # Resolve to an absolute path so outputs are predictable regardless of
        # whether the task runs via `tilebox workflow run` (cwd = repo root) or
        # via a deployed release runner (cwd = release cache dir).
        output_base = Path(self.output_dir)
        if not output_base.is_absolute():
            output_base = Path.home() / "signal-verification-outputs"
        destination = output_base / output_slug(self.title)
        destination.mkdir(parents=True, exist_ok=True)
        index_dir = destination / "index-maps"
        index_dir.mkdir(exist_ok=True)

        # --- Save optical GIF and contact sheet ---
        optical_gif = destination / "optical-natural-color.gif"
        optical_sheet = destination / "optical-contact-sheet.png"
        save_gif(natural_frames, optical_gif, self.frame_duration_ms)
        save_contact_sheet(natural_frames, optical_sheet)

        # --- Spectral indices (before vs after) ---
        pre_scene = [s for s in optical_scenes if s.phase == "BEFORE EVENT"][-1]
        post_scene = [s for s in optical_scenes if s.phase == "AFTER EVENT"][0]

        bands_needed: set[str] = set()
        for idx_name in requested_indices:
            for band in INDEX_BANDS[idx_name]:
                bands_needed.add(band)

        context.logger.info("Reading spectral bands", bands=sorted(bands_needed))
        pre_bands = {b: read_band(pre_scene, b, target_crs, target_transform, output_shape) for b in bands_needed}
        post_bands = {b: read_band(post_scene, b, target_crs, target_transform, output_shape) for b in bands_needed}

        index_results: dict[str, dict[str, Any]] = {}
        for idx_name in requested_indices:
            bands = INDEX_BANDS[idx_name]
            pre_index = INDEX_FUNCS[idx_name]({b: pre_bands[b] for b in bands})
            post_index = INDEX_FUNCS[idx_name]({b: post_bands[b] for b in bands})
            stats = compute_index_stats(pre_index, post_index, pixel_area_m2)
            index_results[idx_name] = stats

            cfg = INDEX_CONFIG[idx_name]
            save_index_png(pre_index, index_dir / f"{idx_name}-before.png",
                           cfg["title"], cfg["label"], cfg["vmin"], cfg["vmax"], cfg["cmap"])
            save_index_raster(pre_index, index_dir / f"{idx_name}-before.tif",
                              target_crs, target_transform)
            change = post_index - pre_index
            save_change_png(change, index_dir / f"{idx_name}-change.png",
                           f"{cfg['title']} — change (after minus before)", cfg["label"])
            context.logger.info("Computed index", index=idx_name, **stats)

        # --- SAR backscatter change ---
        sar_results: dict[str, dict[str, Any]] = {}
        sar_outputs: dict[str, str] = {}
        if len(sar_scenes) >= 2:
            sar_before = [s for s in sar_scenes if s.phase == "BEFORE EVENT"][-1]
            sar_after = [s for s in sar_scenes if s.phase == "AFTER EVENT"][0]
            for pol in ("vv", "vh"):
                try:
                    change = sar_backscatter_change(
                        sar_before, sar_after, target_crs, target_transform, output_shape, pol,
                    )
                    stats = compute_sar_stats(change, pixel_area_m2)
                    sar_results[pol] = stats
                    sar_png = destination / f"sar-{pol}-change.png"
                    save_change_png(change, sar_png,
                                   f"SAR {pol.upper()} backscatter change (dB)",
                                   f"Δ{pol.upper()} (dB)", vmax=5.0)
                    sar_outputs[f"sar_{pol}_change"] = str(sar_png)
                    context.logger.info("Computed SAR change", polarization=pol, **stats)
                except Exception as exc:
                    context.logger.warning(f"SAR {pol} change failed", error=str(exc))

        # --- Build JSON verification report ---
        outputs_map = {
            "optical_natural_color_gif": str(optical_gif),
            "optical_contact_sheet": str(optical_sheet),
            "index_maps_dir": str(index_dir),
        }
        outputs_map.update(sar_outputs)

        report = build_report(
            title=self.title,
            event_date=event_date,
            description=self.description,
            aoi=aoi,
            search_start=start,
            search_end=end,
            optical_scenes=optical_scenes,
            sar_scenes=sar_scenes,
            index_results=index_results,
            sar_results=sar_results,
            outputs=outputs_map,
            pixel_area_m2=pixel_area_m2,
        )
        report_path = destination / "verification-report.json"
        save_report(report, report_path)
        report["outputs"]["verification_report"] = str(report_path)

        context.logger.info(
            "Signal verification complete",
            verdict=report["summary"]["verdict"],
            confidence=report["summary"]["confidence"],
            total_changed_pixels=report["summary"]["total_changed_pixels"],
            optical_scenes=total_optical,
            sar_scenes=len(sar_scenes),
            report=str(report_path),
            output_dir=str(destination),
        )
