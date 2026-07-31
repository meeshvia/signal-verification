"""Sentinel-1 SAR backscatter change detection.

Reads VV/VH backscatter GeoTIFFs from public Microsoft Planetary Computer
Azure Blob Storage URLs returned by the Tilebox dataset query.
SAR sees through clouds and works at night — critical for landslide
verification during rainy season when optical imagery is often cloud-obscured.
"""
from __future__ import annotations

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject, transform_bounds
from shapely.geometry import shape
from rasterio.transform import from_bounds

from .catalog import Acquisition


def sar_backscatter_change(
    before: Acquisition,
    after: Acquisition,
    dst_crs: str,
    dst_transform,
    shape_: tuple[int, int],
    polarization: str = "vv",
) -> np.ndarray:
    """Compute dB backscatter difference (after - before) for a polarization.

    Large positive changes can indicate new structures or rough surfaces.
    Large negative changes can indicate vegetation loss, flooding, or
    smoothed terrain.  Landslide scars typically show a mixed pattern:
    decreased backscatter in the slide area (vegetation stripped) with
    increased backscatter at the toe (debris accumulation).
    """
    before_data = _read_sar_band(before, polarization, dst_crs, dst_transform, shape_)
    after_data = _read_sar_band(after, polarization, dst_crs, dst_transform, shape_)
    before_db = 10.0 * np.log10(np.clip(before_data, 1e-10, None))
    after_db = 10.0 * np.log10(np.clip(after_data, 1e-10, None))
    return after_db - before_db


def _read_sar_band(
    scene: Acquisition, asset: str, dst_crs: str, dst_transform, shape_: tuple[int, int]
) -> np.ndarray:
    mosaic = np.full(shape_, np.nan, dtype=np.float32)
    for item in scene.items:
        href = item.get("assets", {}).get(asset, {}).get("href")
        if not href:
            continue
        with rasterio.Env(AZURE_NO_SIGN_REQUEST="YES"):
            with rasterio.open(href) as src:
                warped = np.full(shape_, np.nan, dtype=np.float32)
                reproject(
                    source=rasterio.band(src, 1),
                    destination=warped,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    src_nodata=src.nodata,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    dst_nodata=np.nan,
                    resampling=Resampling.bilinear,
                )
                fill = np.isnan(mosaic) & np.isfinite(warped)
                mosaic[fill] = warped[fill]
    if np.isnan(mosaic).all():
        raise RuntimeError(f"No readable {asset!r} SAR data for {scene.date_label}")
    return mosaic
