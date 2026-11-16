"""Exporta para o frontend:
- Client/public/data/earth_grid.json  (só se a grade existir)
- Client/public/data/metadata.json
- Client/src/data/targets.json        (textos mantidos, params reais + sources)

Recusa exportar se o 60_validate.py tiver encontrado erro (use --force para ignorar).
"""

import json

import numpy as np
from _common import setup, step

from seeyou_server.export import FIELDS, build_earth_grid, build_metadata, write_json, write_targets_json


def main() -> None:
    cfg, args = setup(__doc__, lambda p: p.add_argument("--force", action="store_true"))
    report = cfg.interim_file("validation_report.md")
    if not report.exists():
        raise SystemExit("rode 60_validate.py antes do export")
    if "**Resultado:** FALHOU" in report.read_text(encoding="utf-8") and not args.force:
        raise SystemExit(f"validação falhou (ver {report}); corrija ou use --force")

    pub = cfg.path("public_data")
    targets = json.loads(cfg.interim_file("targets.json").read_text(encoding="utf-8"))
    stats: dict = {"targets": len(targets)}
    relief_source = cfg["relief"]["source"]

    grid_path = cfg.interim_file("earth_grid.npz")
    if grid_path.exists():
        with np.load(grid_path) as d:
            land = d["land"]
            fields = {f: d[f] for f in FIELDS}
            relief_source = str(d["relief_source"])
        with step("earth_grid.json"):
            grid = build_earth_grid(fields, land, cfg.res_deg, cfg["export"]["digits"])
            size = write_json(grid, pub / "earth_grid.json")
            stats["land_cells"] = len(grid["cells"])
            stats["earth_grid_bytes"] = size
            print(f"  {len(grid['cells'])} células, {size / 1e6:.1f} MB (o GitHub Pages serve com gzip)")
    else:
        print("AVISO: earth_grid.npz não existe; earth_grid.json não foi gerado (o frontend segue no mock)")

    with step("targets.json"):
        write_targets_json(targets, cfg.path("frontend_targets"))
    with step("metadata.json"):
        meta_cfg = dict(cfg["metadata"]) | {"res_deg": cfg.res_deg}
        period = (cfg["period"]["start_year"], cfg["period"]["end_year"])
        write_json(build_metadata(meta_cfg, period, relief_source, stats), pub / "metadata.json", compact=False)


if __name__ == "__main__":
    main()
