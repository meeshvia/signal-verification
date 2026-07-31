from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import numpy as np
import rasterio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject, transform_bounds
from shapely.geometry import shape

from .catalog import Acquisition, group_acquisitions, parse_datetime, search_sentinel2, select_acquisitions
from .indices import INDEX_CONFIG, INDEX_BANDS, bsi, mndwi, nbr, ndmi, ndvi, ndwi, normalized_difference


def validate_aoi(aoi: dict[str, Any]) -> None:
    geometry = shape(aoi)
    if geometry.geom_type not in {"Polygon", "MultiPolygon"} or not geometry.is_valid or geometry.is_empty:
        raise ValueError("aoi_geojson must be a valid non-empty Polygon or MultiPolygon")
    minx, miny, maxx, maxy = geometry.bounds
    if not (-180 <= minx < maxx <= 180 and -90 <= miny < maxy <= 90):
        raise ValueError("aoi_geojson coordinates must be WGS84 longitude/latitude")


def output_slug(title: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return value or "signal-verification"


def output_grid(aoi: dict[str, Any], width: int):
    bounds = shape(aoi).bounds
    projected = transform_bounds("EPSG:4326", "EPSG:3857", *bounds, densify_pts=21)
    aspect = (projected[3] - projected[1]) / (projected[2] - projected[0])
    height = max(240, min(1800, round(width * aspect)))
    return "EPSG:3857", from_bounds(*projected, width, height), (height, width)


def read_visual(scene: Acquisition, dst_crs, dst_transform, shape_: tuple[int, int]) -> np.ndarray:
    channels = [mosaic_asset(scene, "visual", band, dst_crs, dst_transform, shape_) for band in (1, 2, 3)]
    return np.nan_to_num(np.stack(channels, axis=-1), nan=0).clip(0, 255).astype(np.uint8)


def read_band(scene: Acquisition, asset: str, dst_crs, dst_transform, shape_: tuple[int, int]) -> np.ndarray:
    return mosaic_asset(scene, asset, 1, dst_crs, dst_transform, shape_)


def mosaic_asset(scene: Acquisition, asset: str, band: int, dst_crs, dst_transform, shape_: tuple[int, int]):
    mosaic = np.full(shape_, np.nan, dtype=np.float32)
    for item in scene.items:
        href = item.get("assets", {}).get(asset, {}).get("href")
        if not href:
            continue
        with rasterio.Env(AWS_NO_SIGN_REQUEST="YES", GDAL_HTTP_MULTIRANGE="YES"):
            with rasterio.open(href) as src:
                warped = np.full(shape_, np.nan, dtype=np.float32)
                reproject(
                    source=rasterio.band(src, band),
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
        raise RuntimeError(f"No readable {asset!r} data for {scene.date_label}")
    return mosaic


def save_index_raster(data: np.ndarray, path: Path, crs, transform) -> None:
    with rasterio.open(
        path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1], count=1,
        dtype="float32", crs=crs, transform=transform, nodata=np.nan, compress="deflate",
    ) as dst:
        dst.write(data.astype(np.float32), 1)


def save_index_png(
    data: np.ndarray, path: Path, title: str, label: str, vmin: float, vmax: float, cmap: str
) -> None:
    figure, axis = plt.subplots(figsize=(9, 7), constrained_layout=True)
    image = axis.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax)
    axis.set_title(title)
    axis.set_axis_off()
    figure.colorbar(image, ax=axis, shrink=0.75, label=label)
    figure.savefig(path, dpi=140)
    plt.close(figure)


def save_change_png(
    data: np.ndarray, path: Path, title: str, label: str, vmax: float = 0.5
) -> None:
    figure, axis = plt.subplots(figsize=(9, 7), constrained_layout=True)
    image = axis.imshow(data, cmap="RdBu", vmin=-vmax, vmax=vmax)
    axis.set_title(title)
    axis.set_axis_off()
    figure.colorbar(image, ax=axis, shrink=0.75, label=label)
    figure.savefig(path, dpi=140)
    plt.close(figure)


def label_frame(frame: np.ndarray, title: str, scene: Acquisition, recipe: str) -> Image.Image:
    image = Image.fromarray(frame, "RGB")
    panel = 84
    canvas = Image.new("RGB", (image.width, image.height + panel), "#111827")
    canvas.paste(image, (0, panel))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=18)
    small = ImageFont.load_default(size=14)
    draw.text((18, 10), title, fill="white", font=font)
    draw.text((18, 38), f"{scene.date_label}  ·  {scene.phase}", fill="#fbbf24", font=small)
    draw.text((18, 59), recipe, fill="#d1d5db", font=small)
    return canvas


def save_gif(frames: list[Image.Image], path: Path, duration_ms: int) -> None:
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=duration_ms, loop=0, disposal=2)


def save_contact_sheet(frames: list[Image.Image], path: Path) -> None:
    columns = min(3, len(frames))
    thumb_width = 420
    thumbs = []
    for frame in frames:
        thumb = frame.copy()
        thumb.thumbnail((thumb_width, 520), Image.Resampling.LANCZOS)
        thumbs.append(thumb)
    rows = math.ceil(len(thumbs) / columns)
    cell_height = max(thumb.height for thumb in thumbs)
    sheet = Image.new("RGB", (columns * thumb_width, rows * cell_height), "#030712")
    for index, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((index % columns) * thumb_width, (index // columns) * cell_height))
    sheet.save(path)
