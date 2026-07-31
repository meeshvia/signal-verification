"""Spectral indices for ground-event verification.

All indices use Sentinel-2 L2A bands available credential-free from the
Tilebox Sentinel-2 L2A dataset (open_data.aws_earth.sentinel2).
"""
from __future__ import annotations

import numpy as np


def normalized_difference(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute (a-b)/(a+b), retaining invalid and zero-denominator pixels as NaN."""
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    denominator = a + b
    result = np.full(np.broadcast_shapes(a.shape, b.shape), np.nan, dtype=np.float32)
    valid = np.isfinite(a) & np.isfinite(b) & (denominator != 0)
    np.divide(a - b, denominator, out=result, where=valid)
    return result


# --- Individual index definitions ---

def ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """Normalised Difference Water Index — open water bodies.

    Detects water appearance/disappearance: flooding, dam events, drainage.
    Range: -1 (dry) to +1 (water).
    """
    return normalized_difference(green, nir)


def mndwi(green: np.ndarray, swir1: np.ndarray) -> np.ndarray:
    """Modified NDWI — water in shadowed or built-up terrain.

    Better than NDWI for distinguishing water from shadows and bare soil,
    which is critical in mountainous landslide-prone areas.
    Range: -1 (dry) to +1 (water).
    """
    return normalized_difference(green, swir1)


def bsi(swir1: np.ndarray, red: np.ndarray, nir: np.ndarray, blue: np.ndarray) -> np.ndarray:
    """Bare Soil Index — exposed soil and bare ground.

    Detects land clearing, new roads, earthworks, and landslide scars that
    expose bare soil previously covered by vegetation.
    Range: roughly -1 (vegetated) to +1 (bare).
    """
    swir1 = np.asarray(swir1, dtype=np.float32)
    red = np.asarray(red, dtype=np.float32)
    nir = np.asarray(nir, dtype=np.float32)
    blue = np.asarray(blue, dtype=np.float32)
    numerator = (swir1 + red) - (nir + blue)
    denominator = (swir1 + red) + (nir + blue)
    result = np.full(numerator.shape, np.nan, dtype=np.float32)
    valid = np.isfinite(numerator) & np.isfinite(denominator) & (denominator != 0)
    np.divide(numerator, denominator, out=result, where=valid)
    return result


def ndmi(nir: np.ndarray, swir1: np.ndarray) -> np.ndarray:
    """Normalised Difference Moisture Index — vegetation moisture content.

    Detects drought stress, crop drying, and vegetation moisture loss that
    can precede or follow ground events.
    Range: -1 (dry) to +1 (moist).
    """
    return normalized_difference(nir, swir1)


def ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Normalised Difference Vegetation Index — vegetation density and health.

    Detects deforestation, crop destruction, land clearing, and vegetation
    recovery after an event.
    Range: -1 (no vegetation) to +1 (dense vegetation).
    """
    return normalized_difference(nir, red)


def nbr(nir: np.ndarray, swir2: np.ndarray) -> np.ndarray:
    """Normalised Burn Ratio — vegetation moisture and burn change.

    Detects vegetation moisture loss, burn scars, and vegetation damage.
    Range: -1 (burned/dry) to +1 (healthy/moist).
    """
    return normalized_difference(nir, swir2)


# --- Band name constants for Sentinel-2 L2A ---

BAND_GREEN = "green"
BAND_BLUE = "blue"
BAND_RED = "red"
BAND_NIR = "nir"
BAND_NIR08 = "nir08"
BAND_SWIR16 = "swir16"
BAND_SWIR22 = "swir22"

# Maps each index to the bands it needs
INDEX_BANDS = {
    "ndwi": (BAND_GREEN, BAND_NIR),
    "mndwi": (BAND_GREEN, BAND_SWIR16),
    "bsi": (BAND_SWIR16, BAND_RED, BAND_NIR, BAND_BLUE),
    "ndmi": (BAND_NIR, BAND_SWIR16),
    "ndvi": (BAND_NIR, BAND_RED),
    "nbr": (BAND_NIR, BAND_SWIR22),
}

# Display configuration for each index
INDEX_CONFIG = {
    "ndwi": {"label": "NDWI", "title": "Water bodies (NDWI)", "vmin": -1, "vmax": 1, "cmap": "RdYlBu"},
    "mndwi": {"label": "MNDWI", "title": "Water in terrain (MNDWI)", "vmin": -1, "vmax": 1, "cmap": "RdYlBu"},
    "bsi": {"label": "BSI", "title": "Bare soil exposure (BSI)", "vmin": -1, "vmax": 1, "cmap": "RdYlGn_r"},
    "ndmi": {"label": "NDMI", "title": "Vegetation moisture (NDMI)", "vmin": -1, "vmax": 1, "cmap": "RdYlGn"},
    "ndvi": {"label": "NDVI", "title": "Vegetation density (NDVI)", "vmin": -1, "vmax": 1, "cmap": "RdYlGn"},
    "nbr": {"label": "NBR", "title": "Vegetation moisture/burn (NBR)", "vmin": -1, "vmax": 1, "cmap": "RdYlGn"},
}

ALL_INDICES = list(INDEX_BANDS.keys())
