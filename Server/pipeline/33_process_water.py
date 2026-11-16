"""Água da Terra: chuva anual (GPM IMERG) e gelo no subsolo (CCI Permafrost + neve MOD10CM).
Saída: data/interim/water.npz
"""

import numpy as np
from _common import setup, step

from seeyou_server.climate import (combine_ground_ice, list_files, process_permafrost, process_precip,
                                   process_snow)


def main() -> None:
    cfg, _ = setup(__doc__)
    years, res = cfg.years, cfg.res_deg
    out = {}

    prod = cfg["products"]["precip"]
    files = list_files(cfg.raw_dir(prod["short_name"]), ["*.HDF5", "*.h5", "*.hdf5"])
    with step(f"GPM IMERG: {len(files)} arquivo(s)"):
        try:
            out["precip_mm"], n = process_precip(files, years, res, prod.get("min_months", 6))
            print(f"  {n} meses")
        except FileNotFoundError as e:
            print(f"  AVISO: {e}")

    pfr = snow = None
    files = list_files(cfg.raw_dir("cci_permafrost"), ["*.nc"])
    with step(f"CCI Permafrost: {len(files)} arquivo(s)"):
        try:
            pfr, n = process_permafrost(files, years, res)
            out["permafrost_pct"] = pfr
            print(f"  {n} arquivo(s) (região × ano)")
        except FileNotFoundError as e:
            print(f"  AVISO: {e}")

    snow_prod = cfg["products"]["snow"]
    files = list_files(cfg.raw_dir(snow_prod["short_name"]), ["*.hdf"])
    with step(f"MOD10CM: {len(files)} arquivo(s)"):
        try:
            snow, n = process_snow(files, years, res, snow_prod)
            out["snow_min_pct"] = snow
            print(f"  {n} meses")
        except FileNotFoundError as e:
            print(f"  AVISO: {e}")

    if pfr is not None or snow is not None:
        out["ground_ice"] = combine_ground_ice(pfr, snow, cfg["permafrost"]["threshold_pct"],
                                               snow_prod["threshold_pct"])
    if not out:
        print("AVISO: nenhum produto de água disponível; rode 10_download_earth.py")
        return
    path = cfg.interim_file("water.npz")
    np.savez_compressed(path, **out)
    print(f"salvo {path}")


if __name__ == "__main__":
    main()
