from __future__ import annotations

import subprocess
from pathlib import Path


FORBIDDEN_REFERENCES = (
    "/" + "Users/",
    "portfolio" + "-management-system",
    "old" + " project",
    "old" + " repository",
    "existing" + " app",
    "reference" + " app",
    "Local" + " References",
    "local" + " references",
)


def test_tracked_files_do_not_reference_local_paths_or_external_source_history() -> None:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    paths = [Path(item.decode()) for item in result.stdout.split(b"\0") if item]

    violations: list[str] = []
    for path in paths:
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        for forbidden in FORBIDDEN_REFERENCES:
            if forbidden in text:
                violations.append(f"{path}: {forbidden}")

    assert violations == []
