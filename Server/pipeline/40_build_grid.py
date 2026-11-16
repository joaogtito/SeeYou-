"""Junta relevo, temperatura, superfície e água na grade de 0,25° e aplica a máscara de terra.
Saída: data/interim/earth_grid.npz
"""

import numpy as np
from _common import setup, step

from seeyou_server.export import FIELDS
from seeyou_server.grid import grid_shape

SOURCES = {"relief.npz": ["slope_deg", "roughness_m"], "thermal.npz": ["temp_range_k", "temp_min_k"],
           "surface.npz": ["ndvi", "albedo"], "water.npz": ["precip_mm", "ground_ice"]}


def main() -> None:
    cfg, _ = setup(__doc__)
    shape = grid_shape(cfg.res_deg)
    fields = {f: np.full(shape, np.nan, dtype=np.float32) for f in FIELDS}
    relief_path = cfg.interim_file("relief.npz")
    if not relief_path.exists():
        raise SystemExit("relief.npz não existe: rode 30_process_relief.py (ele também gera a máscara de terra)")
    with step("montando a grade"):
        for name, keys in SOURCES.items():
            p = cfg.interim_file(name)
            if not p.exists():
                print(f"  AVISO: {name} ausente -> {', '.join(keys)} ficam nulos")
                continue
            with np.load(p) as d:
                for k in keys:
                    if k in d:
                        fields[k] = d[k].astype(np.float32)
                    else:
                        print(f"  AVISO: {k} ausente em {name}")
        with np.load(relief_path) as d:
            land = d["land_frac"] >= float(cfg["grid"]["land_fraction_min"])
            source = str(d["source"])
        for f in FIELDS:
            fields[f][~land] = np.nan
    out = cfg.interim_file("earth_grid.npz")
    np.savez_compressed(out, land=land, relief_source=np.array(source), **fields)
    print(f"salvo {out}: {int(land.sum())} células de terra")


if __name__ == "__main__":
    main()
