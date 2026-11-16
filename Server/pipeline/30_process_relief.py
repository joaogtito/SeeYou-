"""Relevo da Terra: declividade e rugosidade a ~2 km, média por célula de 0,25°.

Fonte em config.yaml (relief.source): glo90 (padrão, streaming do S3) ou etopo (plano B).
Também gera a máscara de terra (fração de blocos de terra por célula).
Saída: data/interim/relief.npz
"""

from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
from _common import setup, step

from seeyou_server import dem_earth
from seeyou_server.grid import GridAccumulator


def main() -> None:
    cfg, args = setup(__doc__, lambda p: p.add_argument("--max-tiles", type=int, default=None))
    rel = cfg["relief"]
    src, res = rel["source"], cfg.res_deg
    scale = float(cfg["reference_scale_m"])
    cache = None
    if src == "glo90":
        tiles = dem_earth.list_glo90_tiles(cfg.raw_dir("glo90"), stream=rel["stream"])
    else:
        cache = str(cfg.raw_dir("etopo2022_15s"))
        tiles = dem_earth.list_etopo_tiles(cfg.raw_dir("etopo2022_15s"))
    n_max = args.max_tiles or rel.get("max_tiles")
    if n_max:
        tiles = tiles[: int(n_max)]

    acc = {k: GridAccumulator(res) for k in ("slope_deg", "roughness_m")}
    land = GridAccumulator(res)
    errors = []
    with step(f"relevo {src}: {len(tiles)} tiles, {rel['workers']} processos"):
        with ProcessPoolExecutor(max_workers=int(rel["workers"])) as ex:
            futs = [ex.submit(dem_earth.process_tile, t, src, scale, cache) for t in tiles]
            for n, fut in enumerate(as_completed(futs), 1):
                b = fut.result()
                if b is not None and "error" in b:
                    errors.append(str(b["error"]))
                elif b is not None:
                    for k in acc:
                        acc[k].add_points(b["lat"], b["lon"], b[k])
                    land.add_points(b["lat"], b["lon"], b["valid_frac"])
                if n % 500 == 0 or n == len(futs):
                    print(f"  {n}/{len(futs)} tiles")

    # Blocos 100% oceano não chegam aqui; células sem nenhum bloco ficam com fração 0.
    land_frac = np.nan_to_num(land.mean(), nan=0.0)
    out = cfg.interim_file("relief.npz")
    np.savez_compressed(out, slope_deg=acc["slope_deg"].mean(), roughness_m=acc["roughness_m"].mean(),
                        land_frac=land_frac.astype(np.float32), source=np.array(src))
    print(f"salvo {out} | células com terra ≥ {cfg['grid']['land_fraction_min']}: "
          f"{int((land_frac >= cfg['grid']['land_fraction_min']).sum())}")
    if errors:
        print(f"AVISO: {len(errors)} tile(s) com erro (primeiros 5):")
        for e in errors[:5]:
            print("  ", e)


if __name__ == "__main__":
    main()
