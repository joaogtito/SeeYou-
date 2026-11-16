"""Grade global regular em lat/lon (EPSG:4326) e agregação para ela.

Convenção interna: arrays ``(nlat, nlon)`` com a linha 0 no SUL
(centro em ``-90 + res/2``) e a coluna 0 em ``-180 + res/2``.
"""

from __future__ import annotations

import numpy as np


def grid_shape(res: float) -> tuple[int, int]:
    return int(round(180 / res)), int(round(360 / res))


def cell_centers(res: float) -> tuple[np.ndarray, np.ndarray]:
    nlat, nlon = grid_shape(res)
    lats = -90 + (np.arange(nlat) + 0.5) * res
    lons = -180 + (np.arange(nlon) + 0.5) * res
    return lats, lons


def lat_index(lat: np.ndarray | float, res: float) -> np.ndarray:
    nlat, _ = grid_shape(res)
    return np.clip(np.floor((np.asarray(lat) + 90) / res).astype(np.int64), 0, nlat - 1)


def lon_index(lon: np.ndarray | float, res: float) -> np.ndarray:
    _, nlon = grid_shape(res)
    lon = (np.asarray(lon, dtype=np.float64) + 180) % 360
    return np.clip(np.floor(lon / res).astype(np.int64), 0, nlon - 1)


class GridAccumulator:
    """Acumula soma e contagem por célula para tirar a média ignorando NaN."""

    def __init__(self, res: float):
        self.res = res
        self.shape = grid_shape(res)
        n = self.shape[0] * self.shape[1]
        self._sum = np.zeros(n, dtype=np.float64)
        self._cnt = np.zeros(n, dtype=np.float64)

    def add_points(self, lat: np.ndarray, lon: np.ndarray, values: np.ndarray,
                   weights: np.ndarray | None = None) -> None:
        lat = np.asarray(lat).ravel()
        lon = np.asarray(lon).ravel()
        v = np.asarray(values, dtype=np.float64).ravel()
        w = np.ones_like(v) if weights is None else np.asarray(weights, dtype=np.float64).ravel()
        ok = np.isfinite(v) & np.isfinite(lat) & np.isfinite(lon) & (w > 0)
        if not ok.any():
            return
        idx = lat_index(lat[ok], self.res) * self.shape[1] + lon_index(lon[ok], self.res)
        n = self._sum.size
        self._sum += np.bincount(idx, weights=v[ok] * w[ok], minlength=n)
        self._cnt += np.bincount(idx, weights=w[ok], minlength=n)

    def add_regular(self, values: np.ndarray, lat1d: np.ndarray, lon1d: np.ndarray,
                    chunk_rows: int = 256) -> None:
        """Agrega uma grade regular ``values[lat, lon]`` (qualquer ordem de lat)."""
        values = np.asarray(values)
        j = lon_index(lon1d, self.res)
        for r0 in range(0, values.shape[0], chunk_rows):
            block = np.asarray(values[r0:r0 + chunk_rows], dtype=np.float64)
            i = lat_index(lat1d[r0:r0 + chunk_rows], self.res)
            idx = (i[:, None] * self.shape[1] + j[None, :]).ravel()
            v = block.ravel()
            ok = np.isfinite(v)
            if not ok.any():
                continue
            n = self._sum.size
            self._sum += np.bincount(idx[ok], weights=v[ok], minlength=n)
            self._cnt += np.bincount(idx[ok], minlength=n).astype(np.float64)

    @property
    def count(self) -> np.ndarray:
        return self._cnt.reshape(self.shape)

    def mean(self) -> np.ndarray:
        with np.errstate(invalid="ignore", divide="ignore"):
            m = self._sum / self._cnt
        m[self._cnt == 0] = np.nan
        return m.reshape(self.shape).astype(np.float32)


def regular_to_grid(values: np.ndarray, lat1d: np.ndarray, lon1d: np.ndarray, res: float) -> np.ndarray:
    acc = GridAccumulator(res)
    acc.add_regular(values, lat1d, lon1d)
    return acc.mean()


def cmg_centers(res_src: float) -> tuple[np.ndarray, np.ndarray]:
    """Centros da grade CMG dos produtos MODIS (linha 0 no NORTE)."""
    nlat, nlon = grid_shape(res_src)
    lats = 90 - (np.arange(nlat) + 0.5) * res_src
    lons = -180 + (np.arange(nlon) + 0.5) * res_src
    return lats, lons


def nearest_valid(grid: np.ndarray, lat: float, lon: float, res: float, max_cells: int = 2) -> tuple[float, tuple[int, int] | None]:
    """Valor da célula em (lat, lon) ou da vizinha válida mais próxima (até ``max_cells``)."""
    nlat, nlon = grid.shape
    i0, j0 = int(lat_index(lat, res)), int(lon_index(lon, res))
    best = (np.nan, None, 1e9)
    for di in range(-max_cells, max_cells + 1):
        for dj in range(-max_cells, max_cells + 1):
            i, j = i0 + di, (j0 + dj) % nlon
            if 0 <= i < nlat and np.isfinite(grid[i, j]):
                d = di * di + dj * dj
                if d < best[2]:
                    best = (float(grid[i, j]), (i, j), d)
    return best[0], best[1]
