"""Cópia em Python da métrica do frontend (Client/src/lib/metric.ts) para a checagem de sanidade."""

from __future__ import annotations

import math
from typing import Any

DIM_ORDER = ["relevo", "termica", "superficie", "agua", "operacao"]
PARAM_ORDER = ["slope_deg", "roughness_m", "temp_range_k", "temp_min_k",
               "ndvi", "albedo", "precip_mm", "ground_ice", "illumination"]


def illumination_of(lat: float) -> str:
    a = abs(lat)
    return "polar" if a >= 66.5 else "mid" if a >= 23.5 else "tropical"


def param_score(key: str, earth: dict[str, Any], target: dict[str, Any], cfg: dict[str, Any]) -> float | None:
    pc = cfg["params"][key]
    tv = target["params"].get(key)
    if tv is None:
        return None
    if key == "illumination":
        row = cfg["illumination_match"].get(str(tv))
        v = row.get(earth["illumination"]) if row else None
        return float(v) if isinstance(v, (int, float)) else None
    if key == "ground_ice":
        ev = earth.get("ground_ice")
        if ev is None:
            return None
        m = cfg["ground_ice_match"]
        return m["match"] if bool(ev) == bool(tv) else m["mismatch"]
    ev = earth.get(key)
    if ev is None or (isinstance(ev, float) and math.isnan(ev)):
        return None  # regra do plano: faltante = N/A, nunca zero
    sigma = pc.get("sigma") or 1
    if pc.get("one_sided"):
        return math.exp(-max(0.0, ev) / sigma)
    d = (ev - tv) / sigma
    return math.exp(-d * d)


def max_missing(cfg: dict[str, Any]) -> int:
    return int(cfg.get("min_data", {}).get("max_missing", 1))


def score_arrays(fields: dict[str, Any], lat: Any, target: dict[str, Any], cfg: dict[str, Any]):
    """Versão vetorizada de ``compare`` para muitas células (arrays 1D alinhados). NaN = dados insuficientes."""
    import numpy as np

    lat = np.asarray(lat, dtype=np.float64)
    n = lat.size
    dim_sum = {d: np.zeros(n) for d in DIM_ORDER}
    dim_cnt = {d: np.zeros(n) for d in DIM_ORDER}
    n_missing = np.zeros(n)
    a = np.abs(lat)
    band = np.where(a >= 66.5, "polar", np.where(a >= 23.5, "mid", "tropical"))
    for key in PARAM_ORDER:
        pc = cfg["params"][key]
        tv = target["params"].get(key)
        if tv is None:
            continue
        if key == "illumination":
            row = cfg["illumination_match"].get(str(tv))
            if not row:
                continue
            s = np.array([row.get(b, np.nan) for b in ("polar", "mid", "tropical")], dtype=np.float64)
            s = np.where(band == "polar", s[0], np.where(band == "mid", s[1], s[2]))
        elif key == "ground_ice":
            ev = np.asarray(fields["ground_ice"], dtype=np.float64)
            m = cfg["ground_ice_match"]
            s = np.where((ev >= 0.5) == bool(tv), m["match"], m["mismatch"]).astype(np.float64)
            s[~np.isfinite(ev)] = np.nan
        else:
            ev = np.asarray(fields[key], dtype=np.float64)
            sigma = pc.get("sigma") or 1
            s = np.exp(-np.maximum(0, ev) / sigma) if pc.get("one_sided") else np.exp(-((ev - tv) / sigma) ** 2)
        ok = np.isfinite(s)
        if key != "illumination":
            n_missing += ~ok
        dim_sum[pc["dim"]][ok] += s[ok]
        dim_cnt[pc["dim"]][ok] += 1
    acc = np.zeros(n)
    wsum = np.zeros(n)
    for d in DIM_ORDER:
        has = dim_cnt[d] > 0
        w = cfg["weights"].get(d, 1)
        acc[has] += w * dim_sum[d][has] / dim_cnt[d][has]
        wsum[has] += w
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(wsum > 0, acc / wsum, 0.0)
    out[n_missing > max_missing(cfg)] = np.nan
    return out


def compare(earth: dict[str, Any], target: dict[str, Any], cfg: dict[str, Any]) -> float | None:
    """Nota total; None = dados insuficientes (mais de min_data.max_missing parâmetros aplicáveis sem dado)."""
    dims: dict[str, list[float]] = {d: [] for d in DIM_ORDER}
    missing = 0
    for key in PARAM_ORDER:
        s = param_score(key, earth, target, cfg)
        if s is not None:
            dims[cfg["params"][key]["dim"]].append(s)
        elif target["params"].get(key) is not None:
            missing += 1
    if missing > max_missing(cfg):
        return None
    acc = wsum = 0.0
    for d, scores in dims.items():
        if not scores:
            continue
        w = cfg["weights"].get(d, 1)
        acc += w * sum(scores) / len(scores)
        wsum += w
    return acc / wsum if wsum else 0.0
