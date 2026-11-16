import math

import numpy as np
import pytest

from seeyou_server.grid import GridAccumulator, cell_centers, grid_shape, lat_index, lon_index, nearest_valid, regular_to_grid
from seeyou_server.planetary import target_relief
from seeyou_server.relief import RADIUS_M, block_stats, relief_latlon, relief_metric, slope_deg


def test_grid_shape_and_centers():
    assert grid_shape(0.25) == (720, 1440)
    lats, lons = cell_centers(0.25)
    assert lats[0] == pytest.approx(-89.875) and lats[-1] == pytest.approx(89.875)
    assert lons[0] == pytest.approx(-179.875) and lons[-1] == pytest.approx(179.875)


def test_indices_wrap_and_clip():
    assert lat_index(-90, 0.25) == 0 and lat_index(90, 0.25) == 719
    assert lon_index(180, 0.25) == 0  # 180 = -180
    assert lon_index(179.99, 0.25) == 1439


def test_accumulator_mean_ignores_nan():
    acc = GridAccumulator(1.0)
    acc.add_points(np.array([0.5, 0.5, 0.5]), np.array([0.5, 0.5, 0.5]), np.array([1.0, 3.0, np.nan]))
    m = acc.mean()
    assert m[lat_index(0.5, 1.0), lon_index(0.5, 1.0)] == pytest.approx(2.0)
    assert np.isnan(m[0, 0])


def test_regular_to_grid_constant():
    lat = 10 + (np.arange(20) + 0.5) * 0.05  # 10..11°
    lon = 20 + (np.arange(20) + 0.5) * 0.05
    g = regular_to_grid(np.full((20, 20), 7.0), lat, lon, 0.25)
    vals = g[np.isfinite(g)]
    assert vals.size == 16 and np.allclose(vals, 7.0)


def test_nearest_valid_finds_neighbor():
    g = np.full((720, 1440), np.nan, dtype=np.float32)
    i, j = lat_index(-24.07, 0.25), lon_index(-69.87, 0.25)
    g[i + 1, j] = 5
    v, idx = nearest_valid(g, -24.07, -69.87, 0.25)
    assert v == 5 and idx == (i + 1, j)


def test_block_stats_padding_fraction():
    z = np.ones((5, 5))
    mean, std, frac = block_stats(z, 2, 2)
    assert mean.shape == (3, 3)
    assert np.allclose(frac, 1.0)  # bordas parciais não contam padding como "não terra"
    assert np.allclose(std, 0.0)
    z[0, 0] = np.nan
    _, _, frac = block_stats(z, 2, 2)
    assert frac[0, 0] == pytest.approx(0.75)


def test_slope_of_known_plane():
    y, x = np.mgrid[0:50, 0:50] * 100.0  # 100 m de pixel
    z = 0.1 * x  # inclinação 10%
    s = slope_deg(z, 100.0, 100.0)
    assert np.allclose(s, math.degrees(math.atan(0.1)))


def test_relief_metric_plane_and_roughness():
    n, px = 200, 100.0
    y, x = np.mgrid[0:n, 0:n] * px
    z = 0.05 * y
    r = relief_metric(z, px, 2000.0)
    assert r["block_px"] == 20
    assert np.nanmean(r["slope_deg"]) == pytest.approx(math.degrees(math.atan(0.05)), rel=1e-3)
    # std de uma rampa uniforme com 20 amostras de passo 5 m
    expected = np.std(np.arange(20) * 0.05 * px)
    assert np.nanmean(r["roughness_m"]) == pytest.approx(expected, rel=1e-6)


def test_relief_latlon_flat_and_ocean_masked():
    lat = -24 - (np.arange(120) + 0.5) / 120  # 1° em 120 pixels (~925 m)
    lon = -70 + (np.arange(120) + 0.5) / 120
    z = np.full((120, 120), 1000.0)
    z[:, :60] = np.nan  # metade oceano
    r = relief_latlon(z, lat, lon, "earth", 2000.0)
    ok = np.isfinite(r["slope_deg"])
    assert ok.any() and np.allclose(r["slope_deg"][ok], 0.0)
    assert np.allclose(r["roughness_m"][ok], 0.0)
    assert r["valid_frac"].min() == 0.0 and r["valid_frac"].max() == 1.0


def test_relief_latlon_north_south_gradient():
    # rampa norte-sul de 1 m por pixel (~92,6 m a 3")
    n = 1200
    lat = 10 - (np.arange(n) + 0.5) / n
    lon = 20 + (np.arange(n) + 0.5) / n
    z = np.tile(np.arange(n, dtype=float)[:, None], (1, n))
    r = relief_latlon(z, lat, lon, "earth", 2000.0)
    dy = RADIUS_M["earth"] * math.radians(1 / n)
    assert np.nanmedian(r["slope_deg"]) == pytest.approx(math.degrees(math.atan(1 / dy)), rel=0.02)


def test_target_relief_radius_mask():
    n, px = 100, 200.0
    dem = np.zeros((n, n))
    out = target_relief(dem, px, radius_km=5, scale_m=2000.0)
    assert out["slope_deg"] == 0 and out["roughness_m"] == 0
    assert 0 < out["slope_deg_n_blocks"] < (n // 10) ** 2
