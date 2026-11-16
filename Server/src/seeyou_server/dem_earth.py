"""Fontes de DEM da Terra: Copernicus GLO-90 (padrão) e ETOPO 2022 15" (plano B).

Cada fonte expõe ``list_tiles`` e ``read_tile`` → ``(dem, lat1d, lon1d)`` com NaN
no oceano e onde não há dado. A máscara de terra sai do próprio DEM.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import requests

GLO90_BUCKET = "https://copernicus-dem-90m.s3.amazonaws.com"
ETOPO_CATALOG = "https://www.ngdc.noaa.gov/thredds/catalog/global/ETOPO2022/15s/15s_surface_elev_netcdf/catalog.xml"
ETOPO_FILES = "https://www.ngdc.noaa.gov/thredds/fileServer/"


# ---------------------------------------------------------------- listagem

def list_glo90_tiles(local_dir: Path | None = None, stream: bool = True) -> list[str]:
    """Nomes ou caminhos dos tiles GLO-90. Com ``stream`` lê do S3 público via HTTP."""
    if not stream and local_dir is not None:
        return sorted(str(p) for p in Path(local_dir).glob("*.tif"))
    txt = requests.get(f"{GLO90_BUCKET}/tileList.txt", timeout=60).text
    return [t.strip() for t in txt.splitlines() if t.strip()]


def glo90_url(tile: str) -> str:
    if tile.endswith(".tif") or "/" in tile or "\\" in tile:
        return tile
    return f"/vsicurl/{GLO90_BUCKET}/{tile}/{tile}.tif"


def list_etopo_tiles(local_dir: Path | None = None, stream: bool = False) -> list[str]:
    if not stream and local_dir is not None and any(Path(local_dir).glob("*.nc")):
        return sorted(str(p) for p in Path(local_dir).glob("*.nc"))
    xml = requests.get(ETOPO_CATALOG, timeout=60).text
    return [ETOPO_FILES + p for p in re.findall(r'urlPath="([^"]+\.nc)"', xml)]


# ---------------------------------------------------------------- leitura

def read_glo90_tile(tile: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    import rasterio

    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="4",
                      GDAL_HTTP_RETRY_DELAY="2"):
        with rasterio.open(glo90_url(tile)) as ds:
            z = ds.read(1).astype(np.float32)
            nod = ds.nodata
            t = ds.transform
            ny, nx = z.shape
    if nod is not None:
        z[z == nod] = np.nan
    # No GLO-90 o oceano vem achatado em 0 m: tratamos como "não terra".
    z[z == 0] = np.nan
    lat = t.f + (np.arange(ny) + 0.5) * t.e
    lon = t.c + (np.arange(nx) + 0.5) * t.a
    return z, lat, lon


def read_etopo_tile(path_or_url: str, cache_dir: Path | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    from .readers import latlon_names, open_netcdf

    p = path_or_url
    if p.startswith("http"):
        if cache_dir is None:
            raise ValueError("ETOPO por HTTP precisa de cache_dir (baixe no 10_download_earth)")
        p = str(download(p, Path(cache_dir)))
    ds = open_netcdf(p)
    try:
        la, lo = latlon_names(ds)
        z = ds["z"].values.astype(np.float32)
        lat = ds[la].values.astype(np.float64)
        lon = ds[lo].values.astype(np.float64)
    finally:
        ds.close()
    z[~np.isfinite(z) | (z <= 0)] = np.nan  # ETOPO inclui batimetria: terra = acima de 0 m
    return z, lat, lon


def download(url: str, dest_dir: Path, chunk: int = 1 << 20) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / url.rsplit("/", 1)[-1]
    if out.exists() and out.stat().st_size > 0:
        return out
    tmp = out.with_suffix(out.suffix + ".part")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for b in r.iter_content(chunk):
                f.write(b)
    tmp.replace(out)
    return out


def process_tile(tile: str, source: str, scale_m: float, cache_dir: str | None = None) -> dict[str, np.ndarray] | None:
    """Worker (roda em outro processo): lê um tile e devolve os blocos de ~2 km achatados."""
    from .relief import relief_latlon

    try:
        if source == "glo90":
            z, lat, lon = read_glo90_tile(tile)
        else:
            z, lat, lon = read_etopo_tile(tile, Path(cache_dir) if cache_dir else None)
    except Exception as e:  # tile corrompido ou falha de rede: registra e segue
        return {"error": np.array(f"{tile}: {e}")}
    if not np.isfinite(z).any():
        return None
    r = relief_latlon(z, lat, lon, "earth", scale_m, min_valid_frac=0.5)
    keep = np.isfinite(r["valid_frac"])  # blocos de oceano (fração 0) entram na máscara de terra
    return {k: r[k][keep].astype(np.float32) for k in ("lat", "lon", "slope_deg", "roughness_m", "valid_frac")}
