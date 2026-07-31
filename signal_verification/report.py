"""Structured JSON verification report generation."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from .catalog import Acquisition


def compute_index_stats(
    before_index: np.ndarray,
    after_index: np.ndarray,
    pixel_area_m2: float,
) -> dict[str, Any]:
    """Compute change statistics for a single spectral index."""
    diff = after_index - before_index
    valid = np.isfinite(diff)
    valid_diff = diff[valid]
    if valid_diff.size == 0:
        return {
            "before_mean": None,
            "after_mean": None,
            "change_mean": None,
            "changed_pixels": 0,
            "changed_area_km2": 0.0,
        }
    # "Changed" = pixels where the absolute difference exceeds 0.15
    # (empirical threshold for meaningful spectral change)
    changed = np.abs(valid_diff) > 0.15
    return {
        "before_mean": float(np.nanmean(before_index)),
        "after_mean": float(np.nanmean(after_index)),
        "change_mean": float(np.nanmean(valid_diff)),
        "changed_pixels": int(changed.sum()),
        "changed_area_km2": float(changed.sum() * pixel_area_m2 / 1e6),
    }


def compute_sar_stats(
    change_db: np.ndarray,
    pixel_area_m2: float,
    threshold_db: float = 3.0,
) -> dict[str, Any]:
    """Compute statistics for SAR backscatter change."""
    valid = np.isfinite(change_db)
    valid_change = change_db[valid]
    if valid_change.size == 0:
        return {
            "change_mean_db": None,
            "changed_pixels": 0,
            "changed_area_km2": 0.0,
            "max_increase_db": None,
            "max_decrease_db": None,
        }
    changed = np.abs(valid_change) > threshold_db
    return {
        "change_mean_db": float(np.nanmean(valid_change)),
        "changed_pixels": int(changed.sum()),
        "changed_area_km2": float(changed.sum() * pixel_area_m2 / 1e6),
        "max_increase_db": float(np.nanmax(valid_change)),
        "max_decrease_db": float(np.nanmin(valid_change)),
    }


def build_report(
    *,
    title: str,
    event_date: datetime,
    description: str,
    aoi: dict[str, Any],
    search_start: datetime,
    search_end: datetime,
    optical_scenes: list[Acquisition],
    sar_scenes: list[Acquisition],
    index_results: dict[str, dict[str, Any]],
    sar_results: dict[str, dict[str, Any]],
    outputs: dict[str, str],
    pixel_area_m2: float,
) -> dict[str, Any]:
    """Assemble the full JSON verification report."""
    index_summaries = {}
    for name, stats in index_results.items():
        index_summaries[name] = stats

    sar_summary = sar_results if sar_results else None

    # Determine overall verdict
    total_changed = sum(s.get("changed_pixels", 0) for s in index_results.values())
    total_changed += sum(s.get("changed_pixels", 0) for s in sar_results.values())
    if total_changed > 1000:
        verdict = "change_detected"
        confidence = "high" if total_changed > 5000 else "medium"
    elif total_changed > 100:
        verdict = "possible_change"
        confidence = "low"
    else:
        verdict = "no_significant_change"
        confidence = "medium"

    return {
        "event": {
            "title": title,
            "event_date": event_date.isoformat(),
            "description": description,
            "aoi": aoi,
        },
        "search_parameters": {
            "search_start": search_start.isoformat(),
            "search_end": search_end.isoformat(),
            "optical_scene_count": len(optical_scenes),
            "sar_scene_count": len(sar_scenes),
        },
        "scenes": {
            "optical": [
                {
                    "time": s.time.isoformat(),
                    "phase": s.phase,
                    "coverage": s.coverage,
                    "cloud_cover": s.cloud_cover,
                    "item_ids": [item["id"] for item in s.items],
                }
                for s in optical_scenes
            ],
            "sar": [
                {
                    "time": s.time.isoformat(),
                    "phase": s.phase,
                    "coverage": s.coverage,
                    "item_ids": [item["id"] for item in s.items],
                }
                for s in sar_scenes
            ],
        },
        "analysis": {
            "spectral_indices": index_summaries,
            "sar_backscatter": sar_summary,
        },
        "outputs": outputs,
        "summary": {
            "verdict": verdict,
            "confidence": confidence,
            "total_changed_pixels": total_changed,
            "pixel_area_m2": pixel_area_m2,
        },
    }


def save_report(report: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(report, indent=2) + "\n")
