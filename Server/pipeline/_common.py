"""Utilidades compartilhadas pelos scripts numerados (argumentos e log)."""

from __future__ import annotations

import argparse
import sys
import time

from seeyou_server.config import Config, load_config


def setup(description: str, extra=None) -> tuple[Config, argparse.Namespace]:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--config", default=None, help="caminho do config.yaml (padrão: pipeline/config.yaml)")
    if extra:
        extra(p)
    args = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return load_config(args.config), args


class step:
    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        self.t = time.time()
        print(f"==> {self.name}")
        return self

    def __exit__(self, *exc):
        print(f"<== {self.name} ({time.time() - self.t:.1f} s)")
