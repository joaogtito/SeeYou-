"""Downloads: produtos NASA via earthaccess (Earthdata) e ESA CCI Permafrost via CEDA."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from .dem_earth import download as http_download
from .readers import modis_date


def earthdata_login(strategy: str = "netrc", persist: bool = False):
    import earthaccess

    auth = earthaccess.login(strategy=strategy, persist=persist)
    if not auth or not getattr(auth, "authenticated", False):
        raise RuntimeError("login no Earthdata falhou. Rode 00_auth.py (credenciais em ~/.netrc ou ~/_netrc).")
    return auth


def _granule_name(g: Any) -> str:
    links = g.data_links()
    return links[0].rsplit("/", 1)[-1] if links else ""


def filter_days(granules: list[Any], days_of_month: list[int] | None) -> list[Any]:
    """Mantém só granules diários cujo dia do mês está na lista (ex.: MCD43C3)."""
    if not days_of_month:
        return granules
    keep = []
    for g in granules:
        try:
            d = modis_date(_granule_name(g))
        except ValueError:
            continue
        if d.day in days_of_month:
            keep.append(g)
    return keep


def download_product(prod: dict[str, Any], years: list[int], dest: Path, threads: int = 4) -> list[Path]:
    import earthaccess

    start = dt.date(min(years), 1, 1).isoformat()
    end = dt.date(max(years), 12, 31).isoformat()
    kw: dict[str, Any] = {"short_name": prod["short_name"], "temporal": (start, end)}
    if prod.get("version"):
        kw["version"] = str(prod["version"])
    granules = earthaccess.search_data(**kw)
    granules = filter_days(granules, prod.get("days_of_month"))
    if not granules:
        raise RuntimeError(f"nenhum granule encontrado para {kw}")
    dest.mkdir(parents=True, exist_ok=True)
    print(f"  {prod['short_name']}: {len(granules)} arquivo(s) -> {dest}")
    files = earthaccess.download(granules, local_path=str(dest), threads=threads)
    return [Path(f) for f in files if f]


def cci_permafrost_urls(base: str, regions: dict[str, str], years: list[int], version: str) -> list[str]:
    """URLs dos arquivos anuais do CCI Permafrost (um por região e ano)."""
    out = []
    for region, area in regions.items():
        for y in years:
            name = f"ESACCI-PERMAFROST-L4-PFR-MODISLST_CRYOGRID-{area}_PP-{y}-fv{version}.nc"
            out.append(f"{base.rstrip('/')}/v{version}/{region}/{y}/{name}")
    return out


def download_cci_permafrost(cfg_pf: dict[str, Any], years: list[int], dest: Path) -> list[Path]:
    import requests

    got = []
    for url in cci_permafrost_urls(cfg_pf["base_url"], cfg_pf["regions"], years, cfg_pf["version"]):
        try:
            got.append(http_download(url, dest))
        except requests.HTTPError as e:
            # O CCI pode não ter o ano mais recente ainda: segue com os anos disponíveis.
            print(f"  aviso: {url.rsplit('/', 1)[-1]} indisponível ({e.response.status_code})")
    return got
