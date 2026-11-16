"""Montagem dos 6 alvos com valores reais: relevo do DEM + valores publicados com fonte."""

from __future__ import annotations

import copy
import math
from typing import Any

PARAM_KEYS = ["slope_deg", "roughness_m", "temp_range_k", "temp_min_k", "precip_mm",
              "ndvi", "albedo", "illumination", "ground_ice"]

DEM_SOURCE = {
    "moon": "LOLA (LRO), mosaico global LDEM 118 m/px (USGS Astrogeology, Mar 2014)",
    "mars": "MOLA (MGS), mosaico global 463 m/px (USGS Astrogeology)",
}


def build_target(base: dict[str, Any], published: dict[str, Any],
                 relief: dict[str, float] | None) -> dict[str, Any]:
    """Junta o alvo do frontend (textos) com os valores reais e as fontes.

    ``relief`` (se existir) substitui ``slope_deg``/``roughness_m`` publicados.
    """
    t = copy.deepcopy(base)
    params: dict[str, Any] = {}
    sources: dict[str, str] = {}
    confidence: dict[str, str] = {}
    for key in PARAM_KEYS:
        entry = published["params"].get(key)
        if entry is None:
            params[key] = None
            continue
        params[key] = entry["value"]
        src = entry["source"]
        if entry.get("note"):
            src = f"{src}. Nota: {entry['note']}"
        sources[key] = src
        confidence[key] = entry.get("confidence", "published")

    if relief:
        for key in ("slope_deg", "roughness_m"):
            v = relief.get(key)
            if v is not None and math.isfinite(v):
                params[key] = v
                sources[key] = (f"{DEM_SOURCE[base['body']]}: média de {relief.get(key + '_n_blocks', '?')} "
                                f"blocos de ~2 km num raio de {published.get('radius_km')} km do ponto")
                confidence[key] = "computed"

    t["params"] = params
    t["sources"] = sources
    t["confidence"] = confidence
    t["_mock"] = False
    return t


def round_params(params: dict[str, Any], digits: dict[str, int]) -> dict[str, Any]:
    out = {}
    for k, v in params.items():
        if isinstance(v, float) and k in digits:
            d = digits[k]
            out[k] = round(v, d) if d > 0 else int(round(v))
        else:
            out[k] = v
    return out
