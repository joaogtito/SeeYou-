"""Monta os 6 alvos com valores reais: relevo do LOLA/MOLA + valores publicados com fonte.
Saída: data/interim/targets.json
"""

import json
import math

import yaml
from _common import setup, step

from seeyou_server.export import write_targets_json
from seeyou_server.planetary import local_aeqd, target_relief
from seeyou_server.targets import build_target, round_params


def main() -> None:
    cfg, _ = setup(__doc__)
    base = json.loads(cfg.path("frontend_targets").read_text(encoding="utf-8"))
    pub = yaml.safe_load(cfg.path("targets_published").read_text(encoding="utf-8"))
    raw = cfg.raw_dir("moon_mars")
    scale = float(cfg["reference_scale_m"])
    digits = cfg["export"]["digits"]
    out = []
    for t in base:
        p = pub[t["id"]]
        relief = None
        tif = raw / f"{t['id']}.tif"
        with step(t["id"]):
            if tif.exists():
                pix = float(cfg["moon_mars"]["dems"][t["body"]]["pixel_m"])
                dem = local_aeqd(tif, t["lat"], t["lon"], p["radius_km"], t["body"], pix)
                relief = target_relief(dem, pix, p["radius_km"], scale)
                if all(math.isfinite(relief[k]) for k in ("slope_deg", "roughness_m")):
                    print(f"  DEM: declividade {relief['slope_deg']:.2f}°, rugosidade {relief['roughness_m']:.1f} m "
                          f"({relief['slope_deg_n_blocks']} blocos de ~2 km)")
                else:
                    print("  AVISO: relevo do DEM sem valor, usando o publicado")
            else:
                print("  AVISO: sem recorte do DEM (rode 20_download_moon_mars.py); usando relevo publicado")
            nt = build_target(t, p, relief)
            nt["params"] = round_params(nt["params"], digits)
            out.append(nt)
    path = cfg.interim_file("targets.json")
    write_targets_json(out, path)
    print(f"salvo {path}")


if __name__ == "__main__":
    main()
