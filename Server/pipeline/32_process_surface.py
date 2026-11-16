"""Superfície da Terra: NDVI (MOD13C2) e albedo white-sky (MCD43C3). Saída: data/interim/surface.npz"""

import numpy as np
from _common import setup, step

from seeyou_server.climate import list_files, process_cmg_mean


def main() -> None:
    cfg, _ = setup(__doc__)
    out = {}
    for field in ("ndvi", "albedo"):
        prod = cfg["products"][field]
        files = list_files(cfg.raw_dir(prod["short_name"]), ["*.hdf"])
        with step(f"{prod['short_name']}: {len(files)} arquivo(s)"):
            try:
                out[field], n = process_cmg_mean(files, cfg.years, cfg.res_deg, prod)
                print(f"  {n} arquivo(s) no período")
            except FileNotFoundError as e:
                print(f"  AVISO: {e}; campo {field} fica nulo")
    if not out:
        print("AVISO: nenhum produto de superfície disponível; rode 10_download_earth.py")
        return
    path = cfg.interim_file("surface.npz")
    np.savez_compressed(path, **out)
    print(f"salvo {path}")


if __name__ == "__main__":
    main()
