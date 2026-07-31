from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from shapely.wkb import loads as load_wkb
from tilebox.datasets import Client as DatasetClient
from tilebox.datasets.message_pool import get_message_type
from tilebox.datasets.query.time_interval import timestamp_to_datetime
from tilebox.datasets.sync.dataset import _iter_query_pages

SENTINEL2_DATASET = "open_data.aws_earth.sentinel2"
SENTINEL2_COLLECTION = "L2A"

SENTINEL1_DATASET = "tilebox.microsoft_planetary_computer_sentinel1_rtc"
SENTINEL1_COLLECTION = "S1A_IW_RTC"


def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@dataclass(frozen=True)
class Acquisition:
    time: datetime
    items: tuple[dict[str, Any], ...]
    coverage: float
    cloud_cover: float
    sensor: str = ""
    phase: str = ""

    @property
    def date_label(self) -> str:
        return self.time.date().isoformat()


def _extract_stac_assets(msg: Any) -> dict[str, dict[str, Any]]:
    """Extract STAC asset hrefs from a Sentinel-2 protobuf datapoint message."""
    assets_field = getattr(msg, "assets", None)
    if assets_field is None or not hasattr(assets_field, "access_profiles"):
        return {}

    access_profiles = list(assets_field.access_profiles)
    result: dict[str, dict[str, Any]] = {}
    for asset in assets_field.assets:
        key = asset.key
        primary = asset.primary
        idx = primary.access_profile_index
        if idx < len(access_profiles):
            base_href = access_profiles[idx].base_href
            full_href = base_href + primary.href
            result[key] = {"href": full_href}
    return result


def _extract_s1_assets(msg: Any) -> dict[str, dict[str, Any]]:
    """Extract asset hrefs from a Sentinel-1 RTC protobuf message.

    S1 RTC messages use simple repeated string fields (asset_names, asset_hrefs)
    rather than the STAC Assets message used by Sentinel-2.
    """
    names = list(msg.asset_names)
    hrefs = list(msg.asset_hrefs)
    result: dict[str, dict[str, Any]] = {}
    for name, href in zip(names, hrefs):
        result[name] = {"href": href}
    return result


def search_sentinel2(aoi: dict[str, Any], start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Query the Tilebox Sentinel-2 L2A dataset for scenes intersecting the AOI.

    Returns STAC-like item dicts with metadata and public COG asset hrefs.
    Only credential needed is TILEBOX_API_KEY.
    """
    client = DatasetClient()
    dataset = client.dataset(SENTINEL2_DATASET)
    collection = dataset.collection(SENTINEL2_COLLECTION)

    pages = _iter_query_pages(
        dataset._service,
        dataset._dataset.id,
        [collection._collection.id],
        (start, end),
        shape(aoi),
        skip_data=False,
        dataset_name=dataset.name,
        show_progress=False,
    )

    items: list[dict[str, Any]] = []
    for page in pages:
        message_type = get_message_type(page.data.type_url)
        for raw_bytes in page.data.value:
            msg = message_type.FromString(raw_bytes)
            time_val = timestamp_to_datetime(msg.time)
            cloud_cover = float(msg.cloud_cover)
            stac_id = str(msg.stac_id)
            datatake = str(msg.datatake_id)
            geom = load_wkb(msg.geometry.wkb)
            assets = _extract_stac_assets(msg)
            items.append(
                {
                    "id": stac_id,
                    "geometry": mapping(geom),
                    "properties": {
                        "datetime": time_val.isoformat(),
                        "eo:cloud_cover": cloud_cover,
                        "s2:datatake_id": datatake,
                    },
                    "assets": assets,
                }
            )
    return items


def search_sentinel1(aoi: dict[str, Any], start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Query the Tilebox Sentinel-1 RTC dataset for scenes intersecting the AOI.

    Returns STAC-like item dicts with VV/VH asset hrefs pointing to public
    Azure Blob Storage GeoTIFFs.  Only credential needed is TILEBOX_API_KEY.
    """
    client = DatasetClient()
    dataset = client.dataset(SENTINEL1_DATASET)
    collection = dataset.collection(SENTINEL1_COLLECTION)

    pages = _iter_query_pages(
        dataset._service,
        dataset._dataset.id,
        [collection._collection.id],
        (start, end),
        shape(aoi),
        skip_data=False,
        dataset_name=dataset.name,
        show_progress=False,
    )

    items: list[dict[str, Any]] = []
    for page in pages:
        message_type = get_message_type(page.data.type_url)
        for raw_bytes in page.data.value:
            msg = message_type.FromString(raw_bytes)
            time_val = timestamp_to_datetime(msg.time)
            geom = load_wkb(msg.geometry.wkb)
            assets = _extract_s1_assets(msg)
            items.append(
                {
                    "id": str(msg.stac_item_id) if hasattr(msg, "stac_item_id") else str(msg.granule_name),
                    "geometry": mapping(geom),
                    "properties": {
                        "datetime": time_val.isoformat(),
                        "eo:cloud_cover": 0.0,
                        "s1:platform": str(msg.platform),
                        "s1:orbit": int(msg.orbit_number),
                        "s1:polarization": str(msg.polarization),
                    },
                    "assets": assets,
                }
            )
    return items


def group_acquisitions(items: list[dict[str, Any]], aoi: dict[str, Any]) -> list[Acquisition]:
    aoi_shape = shape(aoi)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in items:
        properties = item["properties"]
        time = parse_datetime(properties["datetime"])
        datatake = properties.get("s2:datatake_id") or properties.get("s1:orbit") or time.strftime("%Y%m%dT%H%M")
        groups.setdefault((time.date().isoformat(), str(datatake)), []).append(item)

    acquisitions = []
    for grouped_items in groups.values():
        intersecting = [item for item in grouped_items if shape(item["geometry"]).intersects(aoi_shape)]
        if not intersecting:
            continue
        footprint = unary_union([shape(item["geometry"]) for item in intersecting])
        coverage = aoi_shape.intersection(footprint).area / aoi_shape.area
        cloud_values = [item["properties"].get("eo:cloud_cover") for item in intersecting]
        cloud = max(float(v) if v is not None else 0.0 for v in cloud_values)
        sensor = "optical" if any("s2:datatake_id" in i["properties"] for i in intersecting) else "sar"
        acquisitions.append(
            Acquisition(
                time=parse_datetime(intersecting[0]["properties"]["datetime"]),
                items=tuple(intersecting),
                coverage=coverage,
                cloud_cover=cloud,
                sensor=sensor,
            )
        )
    return sorted(acquisitions, key=lambda c: c.time)


def select_acquisitions(
    candidates: list[Acquisition],
    event_date: datetime,
    before_count: int,
    after_count: int,
    max_cloud_cover: float,
    min_coverage: float,
) -> list[Acquisition]:
    eligible = [
        c for c in candidates
        if c.cloud_cover <= max_cloud_cover and c.coverage >= min_coverage
    ]
    before = [c for c in eligible if c.time < event_date][-before_count:]
    after = [c for c in eligible if c.time >= event_date][:after_count]
    if len(before) < before_count or len(after) < after_count:
        raise ValueError(
            "Not enough complete low-cloud acquisitions: "
            f"found {len(before)}/{before_count} before and {len(after)}/{after_count} after. "
            "Increase the search window or max_cloud_cover, lower min_coverage, or request fewer frames."
        )
    return [
        *[Acquisition(**{**c.__dict__, "phase": "BEFORE EVENT"}) for c in before],
        *[Acquisition(**{**c.__dict__, "phase": "AFTER EVENT"}) for c in after],
    ]
