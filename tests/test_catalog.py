"""Tests for catalog query and acquisition grouping logic."""
from datetime import datetime, timezone

from shapely.geometry import shape

from signal_verification.catalog import group_acquisitions, parse_datetime, select_acquisitions


AOI = {
    "type": "Polygon",
    "coordinates": [[
        [13.5, 10.5], [14.5, 10.5], [14.5, 11.5], [13.5, 11.5], [13.5, 10.5]
    ]]
}


def _make_item(item_id, dt, cloud=10, geom_coords=None):
    if geom_coords is None:
        geom_coords = [[
            [13.0, 10.0], [15.0, 10.0], [15.0, 12.0], [13.0, 12.0], [13.0, 10.0]
        ]]
    return {
        "id": item_id,
        "geometry": {"type": "Polygon", "coordinates": geom_coords},
        "properties": {
            "datetime": dt,
            "eo:cloud_cover": cloud,
            "s2:datatake_id": f"dt-{item_id}",
        },
        "assets": {"visual": {"href": "https://example.com/visual.tif"}},
    }


def test_parse_datetime_with_z():
    result = parse_datetime("2025-07-15T00:00:00Z")
    assert result.tzinfo is not None
    assert result.year == 2025


def test_parse_datetime_naive_assumes_utc():
    result = parse_datetime("2025-07-15")
    assert result.tzinfo == timezone.utc


def test_group_acquisitions_basic():
    items = [
        _make_item("a", "2025-07-10T10:00:00Z", cloud=5),
        _make_item("b", "2025-07-12T10:00:00Z", cloud=20),
        _make_item("c", "2025-07-20T10:00:00Z", cloud=10),
    ]
    acquisitions = group_acquisitions(items, AOI)
    assert len(acquisitions) == 3
    assert acquisitions[0].time.date().isoformat() == "2025-07-10"


def test_group_acquisitions_same_datatake():
    # Both items share the same datatake_id so they should merge into one acquisition
    item_a = _make_item("a", "2025-07-10T10:00:00Z", cloud=5)
    item_b = _make_item("b", "2025-07-10T10:00:00Z", cloud=5)
    item_b["properties"]["s2:datatake_id"] = item_a["properties"]["s2:datatake_id"]
    acquisitions = group_acquisitions([item_a, item_b], AOI)
    assert len(acquisitions) == 1
    assert len(acquisitions[0].items) == 2


def test_select_acquisitions_before_after():
    items = [
        _make_item(f"pre-{i}", f"2025-07-{i:02d}T10:00:00Z", cloud=5)
        for i in range(1, 11)
    ] + [
        _make_item(f"post-{i}", f"2025-07-{i:02d}T10:00:00Z", cloud=5)
        for i in range(16, 26)
    ]
    candidates = group_acquisitions(items, AOI)
    event = parse_datetime("2025-07-15")
    selected = select_acquisitions(candidates, event, 2, 2, 60, 0.5)
    before = [s for s in selected if s.phase == "BEFORE EVENT"]
    after = [s for s in selected if s.phase == "AFTER EVENT"]
    assert len(before) == 2
    assert len(after) == 2


def test_select_acquisitions_filters_cloud():
    items = [
        _make_item("clear", "2025-07-10T10:00:00Z", cloud=10),
        _make_item("cloudy", "2025-07-11T10:00:00Z", cloud=90),
        _make_item("after", "2025-07-20T10:00:00Z", cloud=10),
    ]
    candidates = group_acquisitions(items, AOI)
    event = parse_datetime("2025-07-15")
    selected = select_acquisitions(candidates, event, 1, 1, 60, 0.5)
    assert all(s.cloud_cover <= 60 for s in selected)


def test_select_acquisitions_insufficient_raises():
    items = [_make_item("only", "2025-07-10T10:00:00Z", cloud=5)]
    candidates = group_acquisitions(items, AOI)
    event = parse_datetime("2025-07-15")
    try:
        select_acquisitions(candidates, event, 2, 2, 60, 0.5)
        assert False, "Should have raised"
    except ValueError:
        pass
