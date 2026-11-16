"""Produtos climáticos da Terra: temperatura (MOD11C3), NDVI (MOD13C2), albedo (MCD43C3),
chuva (GPM IMERG) e gelo (ESA CCI Permafrost + neve MODIS MOD10CM).

Regra geral: cada arquivo bruto é agregado primeiro para a grade de 0,25°, e as
médias de vários anos são feitas sobre a grade grossa (economiza memória).
"""

from __future__ import annotations

import datetime as dt
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from .grid import GridAccumulator, cmg_centers, regular_to_grid
from .readers import (imerg_date, latlon_names, modis_date, open_netcdf, read_hdf4_sds,
                      read_imerg_month_mm)


class MonthlyStack:
    """Guarda grades por mês do calendário para fazer climatologias."""

    def __init__(self) -> None:
        self.by_month: dict[int, list[np.ndarray]] = defaultdict(list)

    def add(self, date: dt.date, grid: np.ndarray) -> None:
        self.by_month[date.month].append(grid)

    def __len__(self) -> int:
        return sum(len(v) for v in self.by_month.values())

    def monthly_climatology(self) -> np.ndarray:
        """Array ``(12, nlat, nlon)``: média de cada mês sobre os anos."""
        ref = next(iter(self.by_month.values()))[0]
        out = np.full((12,) + ref.shape, np.nan, dtype=np.float32)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            for m, grids in self.by_month.items():
                out[m - 1] = np.nanmean(np.stack(grids), axis=0)
        return out

    def overall_mean(self) -> np.ndarray:
        """Média anual = média das 12 climatologias mensais (cada mês pesa igual)."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanmean(self.monthly_climatology(), axis=0)


def _nan_reduce(fn: Callable, arr: np.ndarray, axis: int = 0) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return fn(arr, axis=axis)


def _in_period(date: dt.date, years: Iterable[int]) -> bool:
    return date.year in set(years)


def _files(d: Path, pattern: str) -> list[Path]:
    return sorted(p for p in d.glob(pattern) if p.is_file())


# ---------------------------------------------------------------- temperatura

def process_thermal(files: list[Path], years: list[int], res: float, prod: dict) -> dict[str, np.ndarray]:
    """MOD11C3: amplitude dia−noite (média anual) e mínima (menor média mensal noturna)."""
    lat, lon = cmg_centers(prod.get("src_res_deg", 0.05))
    day_s, night_s, diff_s = MonthlyStack(), MonthlyStack(), MonthlyStack()
    for f in files:
        d = modis_date(f)
        if not _in_period(d, years):
            continue
        kw = dict(scale=prod["scale"], fill=[0])
        day = read_hdf4_sds(f, prod["sds_day"], **kw)
        night = read_hdf4_sds(f, prod["sds_night"], **kw)
        day_s.add(d, regular_to_grid(day, lat, lon, res))
        night_s.add(d, regular_to_grid(night, lat, lon, res))
        diff_s.add(d, regular_to_grid(day - night, lat, lon, res))
    if not len(night_s):
        raise FileNotFoundError("nenhum arquivo MOD11C3 no período")
    temp_min = _nan_reduce(np.nanmin, night_s.monthly_climatology())
    return {"temp_range_k": diff_s.overall_mean(), "temp_min_k": temp_min,
            "_n_files": np.array(len(night_s))}


# ---------------------------------------------------------------- superfície

def process_cmg_mean(files: list[Path], years: list[int], res: float, prod: dict) -> tuple[np.ndarray, int]:
    """Média anual de um SDS CMG (NDVI do MOD13C2, albedo do MCD43C3)."""
    lat, lon = cmg_centers(prod.get("src_res_deg", 0.05))
    st = MonthlyStack()
    for f in files:
        d = modis_date(f)
        if not _in_period(d, years):
            continue
        v = read_hdf4_sds(f, prod["sds"], scale=prod["scale"], fill=prod.get("fill"),
                          valid=tuple(prod["valid_raw"]) if prod.get("valid_raw") else None)
        st.add(d, regular_to_grid(v, lat, lon, res))
    if not len(st):
        raise FileNotFoundError(f"nenhum arquivo de {prod['short_name']} no período")
    return st.overall_mean(), len(st)


# ---------------------------------------------------------------- água

def process_precip(files: list[Path], years: list[int], res: float, min_months: int = 6) -> tuple[np.ndarray, int]:
    """IMERG mensal → chuva anual (mm/ano) = média dos meses disponíveis × 12."""
    st = MonthlyStack()
    for f in files:
        d = imerg_date(f)
        if not _in_period(d, years):
            continue
        mm, lat, lon = read_imerg_month_mm(f)
        st.add(d, regular_to_grid(mm, lat, lon, res))
    if not len(st):
        raise FileNotFoundError("nenhum arquivo GPM IMERG no período")
    clim = st.monthly_climatology()
    n = np.isfinite(clim).sum(axis=0)
    annual = _nan_reduce(np.nanmean, clim) * 12
    annual[n < min_months] = np.nan
    return annual.astype(np.float32), len(st)


def process_permafrost(files: list[Path], years: list[int], res: float, var: str = "PFR",
                       chunk: int = 500) -> tuple[np.ndarray, int]:
    """ESA CCI Permafrost (fração %, grade 0,01°) → fração média por célula, média dos anos."""
    grids = []
    for f in files:
        ds = open_netcdf(f)
        try:
            year = int(np.datetime64(ds["time"].values[0], "Y").astype(int) + 1970)
            if year not in years:
                continue
            la, lo = latlon_names(ds)
            lat = ds[la].values.astype(np.float64)
            lon = ds[lo].values.astype(np.float64)
            acc = GridAccumulator(res)
            for r0 in range(0, lat.size, chunk):
                v = ds[var].isel(time=0, **{la: slice(r0, r0 + chunk)}).values.astype(np.float32)
                v[(v < 0) | (v > 100)] = np.nan
                acc.add_regular(v, lat[r0:r0 + chunk], lon)
            grids.append(acc.mean())
        finally:
            ds.close()
    if not grids:
        raise FileNotFoundError("nenhum arquivo CCI Permafrost no período")
    # NH e Antártida vêm em arquivos separados: média por ano já combina as regiões.
    return _nan_reduce(np.nanmean, np.stack(grids)), len(grids)


def process_snow(files: list[Path], years: list[int], res: float, prod: dict) -> tuple[np.ndarray, int]:
    """MOD10CM → menor cobertura de neve (%) entre as climatologias mensais (meses com luz)."""
    lat, lon = cmg_centers(prod.get("src_res_deg", 0.05))
    st = MonthlyStack()
    for f in files:
        d = modis_date(f)
        if not _in_period(d, years):
            continue
        v = read_hdf4_sds(f, prod["sds"], valid=(0, 100))
        st.add(d, regular_to_grid(v, lat, lon, res))
    if not len(st):
        raise FileNotFoundError("nenhum arquivo MOD10CM no período")
    return _nan_reduce(np.nanmin, st.monthly_climatology()), len(st)


def combine_ground_ice(pfr: np.ndarray | None, snow_min: np.ndarray | None,
                       pfr_threshold: float, snow_threshold: float) -> np.ndarray:
    """1 se permafrost ≥ limiar OU neve/gelo permanente ≥ limiar; NaN se nenhuma fonte tem dado."""
    shape = (pfr if pfr is not None else snow_min).shape
    pfr = np.full(shape, np.nan) if pfr is None else pfr
    snow_min = np.full(shape, np.nan) if snow_min is None else snow_min
    ice = (np.nan_to_num(pfr, nan=-1) >= pfr_threshold) | (np.nan_to_num(snow_min, nan=-1) >= snow_threshold)
    out = ice.astype(np.float32)
    out[~np.isfinite(pfr) & ~np.isfinite(snow_min)] = np.nan
    return out


def list_files(d: Path, patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in patterns:
        out += _files(d, p)
    return sorted(set(out))
