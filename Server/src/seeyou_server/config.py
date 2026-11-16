"""Leitura do config.yaml e resolução de caminhos."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SERVER_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = SERVER_DIR / "pipeline" / "config.yaml"


@dataclass
class Config:
    raw: dict[str, Any]
    base_dir: Path

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)

    def path(self, key: str) -> Path:
        """Caminho de ``paths.<key>``, relativo a ``Server/``."""
        p = Path(self.raw["paths"][key])
        return p if p.is_absolute() else (self.base_dir / p).resolve()

    @property
    def res_deg(self) -> float:
        return float(self.raw["grid"]["res_deg"])

    @property
    def years(self) -> list[int]:
        a, b = self.raw["period"]["start_year"], self.raw["period"]["end_year"]
        return list(range(int(a), int(b) + 1))

    def raw_dir(self, name: str) -> Path:
        d = self.path("raw") / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def interim_file(self, name: str) -> Path:
        d = self.path("interim")
        d.mkdir(parents=True, exist_ok=True)
        return d / name


def load_config(path: str | Path | None = None) -> Config:
    p = Path(path) if path else DEFAULT_CONFIG
    with open(p, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Config(raw=raw, base_dir=SERVER_DIR)
