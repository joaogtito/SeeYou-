"""Validação dos dados reais antes de remover o mock (seção 7 do plano).

- Faixa física fora do esperado  -> ERRO (bloqueia o export).
- Cobertura baixa, pontos de controle estranhos, métrica fora do esperado -> AVISO.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .grid import cell_centers, nearest_valid
from .metric import score_arrays

OPS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge, "==": operator.eq}


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_markdown(self) -> str:
        out = ["# Relatório de validação do pipeline", ""]
        out.append(f"**Resultado:** {'OK' if self.ok else 'FALHOU'} "
                   f"({len(self.errors)} erro(s), {len(self.warnings)} aviso(s))")
        out.append("")
        if self.errors:
            out += ["## Erros (bloqueiam o export)", ""] + [f"- {e}" for e in self.errors] + [""]
        if self.warnings:
            out += ["## Avisos", ""] + [f"- {w}" for w in self.warnings] + [""]
        out += self.lines
        return "\n".join(out) + "\n"


def check_ranges(fields: dict[str, np.ndarray], land: np.ndarray, ranges: dict[str, list[float]], rep: Report) -> None:
    rep.lines += ["## Faixas físicas", "", "| campo | mín | máx | faixa aceita | fora da faixa |", "|---|---|---|---|---|"]
    for name, (lo, hi) in ranges.items():
        if name not in fields:
            continue
        v = fields[name][land]
        v = v[np.isfinite(v)]
        if v.size == 0:
            rep.lines.append(f"| {name} | – | – | {lo} – {hi} | sem dado |")
            continue
        bad = int(((v < lo) | (v > hi)).sum())
        rep.lines.append(f"| {name} | {v.min():.3g} | {v.max():.3g} | {lo} – {hi} | {bad} |")
        if bad:
            rep.errors.append(f"{name}: {bad} célula(s) fora da faixa física [{lo}, {hi}] "
                              f"(mín {v.min():.3g}, máx {v.max():.3g})")
    rep.lines.append("")


def check_coverage(fields: dict[str, np.ndarray], land: np.ndarray, min_frac: float, rep: Report,
                   lat_ranges: dict[str, list[float]] | None = None, res: float | None = None) -> None:
    """Fração de células de terra com valor. `lat_ranges` limita a conta de um campo a uma faixa de latitude
    (ex.: ndvi: [-60, 90], porque o MOD13C2 não cobre a Antártida)."""
    lat_ranges = lat_ranges or {}
    n_all = int(land.sum())
    rep.lines += ["## Cobertura (células de terra com valor)", "", f"Total de células de terra: {n_all}", "",
                  "| campo | preenchidas | % | faixa de latitude |", "|---|---|---|---|"]
    lat2d = None
    if lat_ranges:
        res = res or 180.0 / land.shape[0]
        lat1d = -90 + res / 2 + np.arange(land.shape[0]) * res
        lat2d = np.broadcast_to(lat1d[:, None], land.shape)
    for name, arr in fields.items():
        mask = land
        rng = lat_ranges.get(name)
        if rng is not None and lat2d is not None:
            mask = land & (lat2d >= rng[0]) & (lat2d <= rng[1])
        n = int(mask.sum())
        k = int(np.isfinite(arr[mask]).sum())
        frac = k / n if n else 0.0
        faixa = f"{rng[0]}° a {rng[1]}°" if rng is not None else "todas"
        rep.lines.append(f"| {name} | {k} | {100 * frac:.1f}% | {faixa} |")
        if frac < min_frac:
            rep.warnings.append(f"{name}: só {100 * frac:.1f}% das células de terra têm valor (mínimo {100 * min_frac:.0f}%)")
    rep.lines.append("")


def check_control_points(fields: dict[str, np.ndarray], res: float, curated: list[dict[str, Any]],
                         checks: dict[str, dict[str, list]], rep: Report) -> None:
    rep.lines += ["## Pontos de controle", ""]
    by_id = {c["id"]: c for c in curated}
    names = list(fields)
    rep.lines += ["| ponto | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for pid, c in by_id.items():
        row = []
        for name in names:
            v, _ = nearest_valid(fields[name], c["lat"], c["lon"], res)
            row.append("–" if not np.isfinite(v) else f"{v:.3g}")
            rule = checks.get(pid, {}).get(name)
            if rule is None:
                continue
            op, ref = rule
            if not np.isfinite(v):
                rep.warnings.append(f"{pid}: {name} sem valor (esperado {op} {ref})")
            elif not OPS[op](v, ref):
                rep.warnings.append(f"{pid}: {name} = {v:.3g}, esperado {op} {ref}")
        rep.lines.append(f"| {pid} | " + " | ".join(row) + " |")
    for pid in checks:
        if pid not in by_id:
            rep.warnings.append(f"ponto de controle '{pid}' não está em curated.json")
    rep.lines.append("")


def check_metric(fields: dict[str, np.ndarray], land: np.ndarray, res: float, targets: list[dict[str, Any]],
                 sigmas: dict[str, Any], expected: list[dict[str, Any]], rep: Report) -> None:
    """Os análogos clássicos precisam ficar bem colocados no ranking de cada alvo."""
    lats, lons = cell_centers(res)
    ii, jj = np.nonzero(land)
    lat = lats[ii]
    lon = lons[jj]
    flat = {k: v[ii, jj] for k, v in fields.items()}
    by_id = {t["id"]: t for t in targets}
    rep.lines += ["## Sanidade da métrica", "",
                  "| alvo | região esperada | melhor nota na região | percentil no globo | exigido |",
                  "|---|---|---|---|---|"]
    for e in expected:
        t = by_id.get(e["target"])
        if t is None:
            rep.warnings.append(f"alvo '{e['target']}' não encontrado para a checagem da métrica")
            continue
        s = score_arrays(flat, lat, t, sigmas)
        la0, la1, lo0, lo1 = e["bbox"]
        inside = (lat >= la0) & (lat <= la1) & (lon >= lo0) & (lon <= lo1)
        if not inside.any():
            rep.warnings.append(f"{e['target']}: nenhuma célula de terra na região '{e['name']}'")
            continue
        scored = np.isfinite(s)
        if not (inside & scored).any():
            rep.warnings.append(f"{e['target']}: região '{e['name']}' sem células com dados suficientes")
            continue
        best = float(s[inside & scored].max())
        pct = float((s[scored] < best).mean() * 100)
        need = float(e.get("min_percentile", 90))
        rep.lines.append(f"| {e['target']} | {e['name']} | {best:.3f} | {pct:.1f} | ≥ {need:.0f} |")
        if pct < need:
            rep.warnings.append(f"{e['target']}: '{e['name']}' ficou no percentil {pct:.1f} (esperado ≥ {need:.0f}). "
                                "Investigar σ ou dado antes da apresentação.")
    rep.lines.append("")


def validate_targets(targets: list[dict[str, Any]], ranges: dict[str, list[float]], rep: Report) -> None:
    for t in targets:
        for k, v in t["params"].items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and k in ranges:
                lo, hi = ranges[k]
                if not (lo <= v <= hi):
                    rep.errors.append(f"alvo {t['id']}: {k} = {v} fora de [{lo}, {hi}]")
            if k not in t.get("sources", {}) and v is not None:
                rep.warnings.append(f"alvo {t['id']}: {k} sem fonte registrada")
