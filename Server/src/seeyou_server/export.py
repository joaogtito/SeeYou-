"""Exportação para o contrato do frontend (seção 6 do plano)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import numpy as np

from . import PIPELINE_VERSION
from .grid import cell_centers

FIELDS = ["slope_deg", "roughness_m", "temp_range_k", "temp_min_k", "precip_mm", "ndvi", "albedo", "ground_ice"]


def _fmt(v: float, digits: int) -> float | int | None:
    if not np.isfinite(v):
        return None
    if digits <= 0:
        return int(round(float(v)))
    return round(float(v), digits)


def build_earth_grid(fields: dict[str, np.ndarray], land: np.ndarray, res: float,
                     digits: dict[str, int], generated_at: str | None = None) -> dict[str, Any]:
    """Só células de terra; ``[lat, lon, ...valores na ordem de FIELDS]``, ``null`` = sem dado."""
    lats, lons = cell_centers(res)
    ii, jj = np.nonzero(land)
    order = np.lexsort((jj, -ii))  # norte → sul, oeste → leste
    cells = []
    for i, j in zip(ii[order], jj[order]):
        row: list[Any] = [round(float(lats[i]), 4), round(float(lons[j]), 4)]
        for f in FIELDS:
            v = fields[f][i, j] if f in fields else np.nan
            if f == "ground_ice":
                row.append(None if not np.isfinite(v) else int(v >= 0.5))
            else:
                row.append(_fmt(v, digits.get(f, 2)))
        cells.append(row)
    return {
        "_mock": False,
        "res_deg": res,
        "generated_at": generated_at or dt.date.today().isoformat(),
        "fields": FIELDS,
        "cells": cells,
    }


def build_metadata(cfg_meta: dict[str, Any], period: tuple[int, int], relief_source: str,
                   stats: dict[str, Any], generated_at: str | None = None) -> dict[str, Any]:
    fields = {}
    for name, m in cfg_meta["fields"].items():
        entry = dict(m)
        if name in ("slope_deg", "roughness_m"):
            entry = dict(m[relief_source]) | {k: v for k, v in m.items() if not isinstance(v, dict)}
        if entry.get("period") == "config":
            entry["period"] = f"{period[0]}–{period[1]}"
        fields[name] = entry
    return {
        "pipeline_version": PIPELINE_VERSION,
        "generated_at": generated_at or dt.date.today().isoformat(),
        "grid": {"res_deg": cfg_meta.get("res_deg"), "crs": "EPSG:4326", "cell_position": "center",
                 "land_only": True, "missing_value": None},
        "reference_scale_km": cfg_meta.get("reference_scale_km", 2),
        "relief_source": relief_source,
        "fields": fields,
        "derived_in_frontend": cfg_meta.get("derived_in_frontend", {}),
        "fixed_per_body": cfg_meta.get("fixed_per_body", {}),
        "stats": stats,
    }


def write_json(obj: Any, path: Path, compact: bool = True) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    else:
        txt = json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)
    path.write_text(txt + "\n", encoding="utf-8")
    return path.stat().st_size


def write_targets_json(targets: list[dict[str, Any]], path: Path) -> None:
    """Mesmo estilo do arquivo do frontend: um alvo por bloco, indentado."""
    write_json(targets, path, compact=False)
