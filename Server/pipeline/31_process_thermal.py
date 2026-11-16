"""Temperatura da Terra (MOD11C3): amplitude dia − noite e mínima. Saída: data/interim/thermal.npz"""

import numpy as np
from _common import setup, step

from seeyou_server.climate import list_files, process_thermal


def main() -> None:
    cfg, _ = setup(__doc__)
    prod = cfg["products"]["lst"]
    files = list_files(cfg.raw_dir(prod["short_name"]), ["*.hdf"])
    with step(f"MOD11C3: {len(files)} arquivo(s)"):
        try:
            r = process_thermal(files, cfg.years, cfg.res_deg, prod)
        except FileNotFoundError as e:
            print(f"  AVISO: {e}; temp_range_k e temp_min_k ficam nulos (rode 10_download_earth.py)")
            return
    out = cfg.interim_file("thermal.npz")
    np.savez_compressed(out, **r)
    print(f"salvo {out} ({int(r['_n_files'])} meses)")


if __name__ == "__main__":
    main()
