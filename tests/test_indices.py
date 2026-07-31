"""Tests for spectral index computations."""
import numpy as np

from signal_verification.indices import (
    INDEX_BANDS,
    bsi,
    mndwi,
    nbr,
    ndmi,
    ndvi,
    ndwi,
    normalized_difference,
)


def test_normalized_difference_basic():
    a = np.array([5.0, 3.0, 1.0])
    b = np.array([1.0, 3.0, 5.0])
    result = normalized_difference(a, b)
    assert np.isclose(result[0], 4.0 / 6.0)
    assert np.isclose(result[1], 0.0)
    assert np.isclose(result[2], -4.0 / 6.0)


def test_normalized_difference_zero_denominator():
    a = np.array([1.0])
    b = np.array([-1.0])
    result = normalized_difference(a, b)
    assert np.isnan(result[0])


def test_ndwi_water_positive():
    green = np.array([0.3])
    nir = np.array([0.1])
    result = ndwi(green, nir)
    assert result[0] > 0


def test_ndwi_dry_negative():
    green = np.array([0.1])
    nir = np.array([0.5])
    result = ndwi(green, nir)
    assert result[0] < 0


def test_mndwi_basic():
    green = np.array([0.3])
    swir1 = np.array([0.05])
    result = mndwi(green, swir1)
    assert result[0] > 0


def test_bsi_bare_soil_positive():
    swir1 = np.array([0.4])
    red = np.array([0.3])
    nir = np.array([0.1])
    blue = np.array([0.1])
    result = bsi(swir1, red, nir, blue)
    assert result[0] > 0


def test_bsi_vegetated_negative():
    swir1 = np.array([0.1])
    red = np.array([0.1])
    nir = np.array([0.5])
    blue = np.array([0.05])
    result = bsi(swir1, red, nir, blue)
    assert result[0] < 0


def test_ndmi_moist_positive():
    nir = np.array([0.5])
    swir1 = np.array([0.1])
    result = ndmi(nir, swir1)
    assert result[0] > 0


def test_ndvi_dense_vegetation():
    nir = np.array([0.5])
    red = np.array([0.1])
    result = ndvi(nir, red)
    assert result[0] > 0.5


def test_nbr_healthy_positive():
    nir = np.array([0.5])
    swir2 = np.array([0.1])
    result = nbr(nir, swir2)
    assert result[0] > 0


def test_index_bands_cover_all_indices():
    for name, bands in INDEX_BANDS.items():
        assert len(bands) >= 2, f"{name} needs at least 2 bands"
