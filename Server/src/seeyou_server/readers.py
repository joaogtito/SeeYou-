"""Leitores dos formatos brutos (HDF4 do MODIS, HDF5 do GPM, NetCDF do CCI/ETOPO, GeoTIFF)."""

from __future__ import annotations

import calendar
import datetime as dt
import re
from pathlib import Path

import numpy as np


# ---------------------------------------------------------------- MODIS (HDF4)

def read_hdf4_sds(path: str | Path, sds: str, scale: float = 1.0, offset: float = 0.0,
                  fill: list[float] | None = None, valid: tuple[float, float] | None = None) -> np.ndarray:
    """Lê um SDS de um HDF4 do MODIS e aplica escala/fill. Retorna float32 com NaN."""
    from pyhdf.SD import SD, SDC

    f = SD(str(path), SDC.READ)
    try:
        ds = f.select(sds)
        raw = ds.get().astype(np.float64)
        attrs = ds.attributes()
    finally:
        f.end()
    fills = list(fill or [])
    if "_FillValue" in attrs:
        fills.append(float(attrs["_FillValue"]))
    bad = np.zeros(raw.shape, dtype=bool)
    for fv in fills:
        bad |= raw == fv
    if valid is None and "valid_range" in attrs:
        valid = tuple(float(v) for v in attrs["valid_range"])
    if valid is not None:
        bad |= (raw < valid[0]) | (raw > valid[1])
    out = raw * scale + offset
    out[bad] = np.nan
    return out.astype(np.float32)


_MODIS_DATE = re.compile(r"\.A(\d{4})(\d{3})\.")


def modis_date(path: str | Path) -> dt.date:
    """Data do granule a partir do nome (``*.AYYYYDDD.*``)."""
    m = _MODIS_DATE.search(Path(path).name)
    if not m:
        raise ValueError(f"nome MODIS sem data: {path}")
    return dt.date(int(m.group(1)), 1, 1) + dt.timedelta(days=int(m.group(2)) - 1)


# ---------------------------------------------------------------- GPM IMERG (HDF5)

_IMERG_DATE = re.compile(r"3B-MO\.MS\.MRG\.3IMERG\.(\d{4})(\d{2})(\d{2})")


def imerg_date(path: str | Path) -> dt.date:
    m = _IMERG_DATE.search(Path(path).name)
    if not m:
        raise ValueError(f"nome IMERG sem data: {path}")
    return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def read_imerg_month_mm(path: str | Path, var: str = "precipitation") -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Precipitação mensal do IMERG em mm/mês. Retorna (valores[lat, lon], lat, lon)."""
    import h5py

    d = imerg_date(path)
    with h5py.File(path, "r") as f:
        g = f["Grid"]
        rate = g[var][0].astype(np.float64)  # (lon, lat), mm/h
        lat = g["lat"][:].astype(np.float64)
        lon = g["lon"][:].astype(np.float64)
        fv = g[var].attrs.get("_FillValue", -9999.9)
    rate[(rate < 0) | (rate == fv)] = np.nan
    hours = 24 * calendar.monthrange(d.year, d.month)[1]
    return (rate.T * hours).astype(np.float32), lat, lon


# ---------------------------------------------------------------- NetCDF genérico

def open_netcdf(path: str | Path):
    import xarray as xr

    return xr.open_dataset(path, engine="h5netcdf", mask_and_scale=True)


def latlon_names(ds) -> tuple[str, str]:
    lat = next(n for n in ("lat", "latitude", "y") if n in ds.coords or n in ds.variables)
    lon = next(n for n in ("lon", "longitude", "x") if n in ds.coords or n in ds.variables)
    return lat, lon
