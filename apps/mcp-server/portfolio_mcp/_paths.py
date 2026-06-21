from __future__ import annotations

import sys
from pathlib import Path


def configure_monorepo_paths() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    for relative_path in ("packages/policy", "packages/domain"):
        package_path = str(repo_root / relative_path)
        if package_path not in sys.path:
            sys.path.insert(0, package_path)
