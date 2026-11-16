"""Recorta os DEMs LOLA (Lua) e MOLA (Marte) em volta dos 6 alvos.

Lê só as linhas necessárias dos mosaicos globais da USGS via HTTP (alguns MB por alvo)
e salva em data/raw/moon_mars/<id>.tif.
"""

import json

import yaml
from _common import setup, step

from seeyou_server.planetary import read_window, save_geotiff


def main() -> None:
    cfg, _ = setup(__doc__)
    targets = json.loads(cfg.path("frontend_targets").read_text(encoding="utf-8"))
    pub = yaml.safe_load(cfg.path("targets_published").read_text(encoding="utf-8"))
    out = cfg.raw_dir("moon_mars")
    for t in targets:
        body = t["body"]
        dem = cfg["moon_mars"]["dems"][body]
        radius = pub[t["id"]]["radius_km"]
        with step(f"{t['id']} ({body}, {t['lat']}, {t['lon']}, raio {radius} km)"):
            z, tr, crs = read_window(dem["url"], t["lat"], t["lon"], radius, body)
            save_geotiff(out / f"{t['id']}.tif", z, tr, crs)
            print(f"  recorte {z.shape[0]}×{z.shape[1]} px")


if __name__ == "__main__":
    main()
