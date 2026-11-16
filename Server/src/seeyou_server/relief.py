"""Declividade e rugosidade na escala de referência (~2 km), iguais nos três corpos.

- Rugosidade: desvio-padrão da elevação dentro de cada bloco de ~2 km (DEM nativo).
- Declividade: gradiente do DEM reamostrado para ~2 km (média de cada bloco).
"""

from __future__ import annotations

import math

import numpy as np

RADIUS_M = {"earth": 6_371_008.8, "moon": 1_737_400.0, "mars": 3_396_190.0}


def _pad_to_multiple(z: np.ndarray, by: int, bx: int) -> np.ndarray:
    ny, nx = z.shape
    py, px = (-ny) % by, (-nx) % bx
    if py or px:
        z = np.pad(z, ((0, py), (0, px)), constant_values=np.nan)
    return z


def block_stats(z: np.ndarray, by: int, bx: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Média, desvio-padrão e fração de pixels válidos em blocos ``by × bx``.

    Nas bordas incompletas a fração é calculada só sobre os pixels que existem.
    """
    z = np.asarray(z, dtype=np.float64)
    real = _pad_to_multiple(np.ones(z.shape), by, bx)
    z = _pad_to_multiple(z, by, bx)
    ny, nx = z.shape[0] // by, z.shape[1] // bx
    b = z.reshape(ny, by, nx, bx)
    valid = np.isfinite(b)
    n = valid.sum(axis=(1, 3))
    n_real = np.nansum(real.reshape(ny, by, nx, bx), axis=(1, 3))
    s = np.where(valid, b, 0.0).sum(axis=(1, 3))
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = s / n
        sq = np.where(valid, (b - mean[:, None, :, None]) ** 2, 0.0).sum(axis=(1, 3))
        std = np.sqrt(sq / n)
    mean[n == 0] = np.nan
    std[n == 0] = np.nan
    return mean, std, n / np.maximum(n_real, 1)


def slope_deg(z: np.ndarray, dy: float, dx: float | np.ndarray) -> np.ndarray:
    """Declividade em graus. ``dx`` pode variar por linha (grade lat/lon)."""
    z = np.asarray(z, dtype=np.float64)
    if min(z.shape) < 2:
        return np.full(z.shape, np.nan)
    gy = np.gradient(z, axis=0) / abs(dy)
    dxa = np.abs(np.asarray(dx, dtype=np.float64))
    gx = np.gradient(z, axis=1) / (dxa[:, None] if dxa.ndim == 1 else dxa)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def block_size(scale_m: float, pixel_m: float) -> int:
    return max(1, int(round(scale_m / max(pixel_m, 1e-9))))


def relief_latlon(dem: np.ndarray, lat1d: np.ndarray, lon1d: np.ndarray, body: str = "earth",
                  scale_m: float = 2000.0, min_valid_frac: float = 0.5) -> dict[str, np.ndarray]:
    """Relief de um tile em lat/lon. Retorna arrays por bloco (~2 km).

    ``dem`` deve ter NaN onde não é terra/sem dado.
    """
    r = RADIUS_M[body]
    dlat = abs(float(lat1d[1] - lat1d[0])) if len(lat1d) > 1 else 1.0
    dlon = abs(float(lon1d[1] - lon1d[0])) if len(lon1d) > 1 else 1.0
    lat_c = float(np.mean(lat1d))
    dy = r * math.radians(dlat)
    dx = r * math.radians(dlon) * max(math.cos(math.radians(lat_c)), 1e-6)
    by, bx = block_size(scale_m, dy), block_size(scale_m, dx)

    mean, std, frac = block_stats(dem, by, bx)
    blat = _block_centers(np.asarray(lat1d, dtype=np.float64), by)
    blon = _block_centers(np.asarray(lon1d, dtype=np.float64), bx)
    bdx = r * math.radians(dlon * bx) * np.maximum(np.cos(np.radians(blat)), 1e-6)
    slope = slope_deg(mean, dy * by, bdx)

    bad = frac < min_valid_frac
    slope[bad] = np.nan
    std[bad] = np.nan
    lat2, lon2 = np.meshgrid(blat, blon, indexing="ij")
    return {"lat": lat2, "lon": lon2, "slope_deg": slope, "roughness_m": std, "valid_frac": frac}


def relief_metric(dem: np.ndarray, pixel_m: float, scale_m: float = 2000.0,
                  min_valid_frac: float = 0.5) -> dict[str, np.ndarray]:
    """Relief de um DEM já projetado em metros (ex.: azimutal equidistante local).

    Retorna também ``x``/``y`` do centro de cada bloco, com origem no centro do DEM.
    """
    b = block_size(scale_m, pixel_m)
    mean, std, frac = block_stats(dem, b, b)
    slope = slope_deg(mean, pixel_m * b, pixel_m * b)
    bad = frac < min_valid_frac
    slope[bad] = np.nan
    std[bad] = np.nan
    ny, nx = dem.shape
    yc = (np.arange(mean.shape[0]) * b + b / 2) * pixel_m - ny * pixel_m / 2
    xc = (np.arange(mean.shape[1]) * b + b / 2) * pixel_m - nx * pixel_m / 2
    y2, x2 = np.meshgrid(yc, xc, indexing="ij")
    return {"x": x2, "y": y2, "slope_deg": slope, "roughness_m": std, "valid_frac": frac, "block_px": b}


def _block_centers(coord: np.ndarray, b: int) -> np.ndarray:
    n = len(coord)
    nb = -(-n // b)
    step = coord[1] - coord[0] if n > 1 else 0.0
    starts = coord[0] + np.arange(nb) * b * step
    return starts + (b - 1) / 2 * step
