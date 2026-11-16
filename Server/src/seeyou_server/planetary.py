"""DEMs da Lua (LOLA) e de Marte (MOLA) para os 6 alvos.

Lemos só uma faixa pequena dos mosaicos globais da USGS via HTTP (leitura parcial),
reprojetamos para uma projeção azimutal equidistante centrada no alvo (vale também
no polo) e calculamos declividade/rugosidade com as mesmas funções da Terra.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from .relief import RADIUS_M, relief_metric


def read_window(url: str, lat: float, lon: float, radius_km: float, body: str,
                margin: float = 1.6) -> tuple[np.ndarray, object, object]:
    """Lê do mosaico equiretangular as linhas/colunas que cobrem o círculo do alvo."""
    import rasterio
    from rasterio.windows import Window

    r = RADIUS_M[body]
    dlat = math.degrees(radius_km * 1000 * margin / r)
    src = url if url.startswith("/vsi") or Path(url).exists() else f"/vsicurl/{url}"
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="4"):
        with rasterio.open(src) as ds:
            t = ds.transform
            deg_per_m = 180 / (math.pi * r)
            # Mosaicos USGS: x = R·lon, y = R·lat (simple cylindrical, paralelo padrão 0)
            to_row = lambda la: (la / deg_per_m - t.f) / t.e
            to_col = lambda lo: (lo / deg_per_m - t.c) / t.a
            r0 = int(max(0, math.floor(to_row(min(90, lat + dlat)))))
            r1 = int(min(ds.height, math.ceil(to_row(max(-90, lat - dlat)))))
            polar = abs(lat) + dlat >= 80
            if polar:
                c0, c1 = 0, ds.width
            else:
                dlon = dlat / max(math.cos(math.radians(abs(lat) + dlat)), 1e-3)
                c0 = int(max(0, math.floor(to_col(lon - dlon))))
                c1 = int(min(ds.width, math.ceil(to_col(lon + dlon))))
            win = Window(c0, r0, c1 - c0, r1 - r0)
            z = ds.read(1, window=win).astype(np.float32)
            nod = ds.nodata
            scale = ds.scales[0] if ds.scales else 1.0
            offset = ds.offsets[0] if ds.offsets else 0.0
            wt = ds.window_transform(win)
            crs = ds.crs
    if nod is not None:
        z[z == nod] = np.nan
    z = z * float(scale or 1.0) + float(offset or 0.0)
    return z, wt, crs


def save_geotiff(path: Path, z: np.ndarray, transform, crs) -> None:
    import rasterio

    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", driver="GTiff", height=z.shape[0], width=z.shape[1], count=1,
                       dtype="float32", crs=crs, transform=transform, nodata=np.nan,
                       compress="deflate") as dst:
        dst.write(z.astype(np.float32), 1)


def local_aeqd(path: Path, lat: float, lon: float, radius_km: float, body: str,
               pixel_m: float) -> np.ndarray:
    """Reprojeta o recorte salvo para azimutal equidistante centrada em (lat, lon)."""
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject

    r = RADIUS_M[body]
    half = radius_km * 1000 * 1.1
    n = int(math.ceil(2 * half / pixel_m))
    dst_crs = CRS.from_proj4(f"+proj=aeqd +lat_0={lat} +lon_0={lon} +R={r} +units=m +no_defs")
    dst_t = from_origin(-n * pixel_m / 2, n * pixel_m / 2, pixel_m, pixel_m)
    out = np.full((n, n), np.nan, dtype=np.float32)
    with rasterio.open(path) as src:
        reproject(source=rasterio.band(src, 1), destination=out, src_transform=src.transform,
                  src_crs=src.crs, dst_transform=dst_t, dst_crs=dst_crs,
                  resampling=Resampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan)
    return out


def target_relief(dem_aeqd: np.ndarray, pixel_m: float, radius_km: float,
                  scale_m: float = 2000.0) -> dict[str, float]:
    """Média de declividade e rugosidade (~2 km) dentro do raio do alvo."""
    rel = relief_metric(dem_aeqd, pixel_m, scale_m)
    inside = np.hypot(rel["x"], rel["y"]) <= radius_km * 1000
    out = {}
    for k in ("slope_deg", "roughness_m"):
        v = rel[k][inside]
        v = v[np.isfinite(v)]
        out[k] = float(np.mean(v)) if v.size else float("nan")
        out[f"{k}_n_blocks"] = int(v.size)
    return out
