"""Roda o pipeline em ordem. Ex.: uv run python pipeline/run_all.py --from 30 --to 70"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--from", dest="start", default="00")
    p.add_argument("--to", dest="end", default="70")
    p.add_argument("--config", default=None)
    a = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    scripts = sorted(s for s in HERE.glob("[0-9][0-9]_*.py") if a.start <= s.name[:2] <= a.end)
    for s in scripts:
        cmd = [sys.executable, str(s)] + (["--config", a.config] if a.config else [])
        print(f"\n######## {s.name}")
        r = subprocess.run(cmd, cwd=HERE, env=os.environ | {"PYTHONIOENCODING": "utf-8"})
        if r.returncode:
            sys.exit(f"{s.name} terminou com código {r.returncode}")


if __name__ == "__main__":
    main()
