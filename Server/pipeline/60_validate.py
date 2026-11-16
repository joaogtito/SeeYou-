"""Valida grade e alvos (faixas físicas, cobertura, pontos de controle, sanidade da métrica).

Faixa física violada = ERRO (código de saída 1, o export não roda). O resto vira aviso.
Relatório: data/interim/validation_report.md
"""

import json
import sys

import numpy as np
from _common import setup, step

from seeyou_server.export import FIELDS
from seeyou_server.validate import (Report, check_control_points, check_coverage, check_metric, check_ranges,
                                    validate_targets)


def main() -> None:
    cfg, _ = setup(__doc__)
    v = cfg["validation"]
    rep = Report()
    res = cfg.res_deg
    targets = json.loads(cfg.interim_file("targets.json").read_text(encoding="utf-8"))
    with step("alvos"):
        validate_targets(targets, v["target_ranges"], rep)

    grid_path = cfg.interim_file("earth_grid.npz")
    if grid_path.exists():
        with np.load(grid_path) as d:
            land = d["land"]
            fields = {f: d[f] for f in FIELDS}
        curated = json.loads(cfg.path("curated").read_text(encoding="utf-8"))
        sigmas = json.loads(cfg.path("sigmas").read_text(encoding="utf-8"))
        with step("grade da Terra"):
            check_ranges(fields, land, v["ranges"], rep)
            check_coverage(fields, land, float(v["min_coverage"]), rep, v.get("coverage_lat_range"), res)
            check_control_points(fields, res, curated, v["control_points"], rep)
            check_metric(fields, land, res, targets, sigmas, v["expected_analogs"], rep)
    else:
        rep.warnings.append("earth_grid.npz não existe: só os alvos foram validados")

    path = cfg.interim_file("validation_report.md")
    path.write_text(rep.to_markdown(), encoding="utf-8")
    print(f"relatório: {path}")
    for e in rep.errors:
        print("ERRO:", e)
    for w in rep.warnings:
        print("AVISO:", w)
    sys.exit(0 if rep.ok else 1)


if __name__ == "__main__":
    main()
