from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def _compose_command() -> list[str] | None:
    if shutil.which("docker") is not None:
        return ["docker", "compose"]
    if shutil.which("podman") is not None:
        return ["podman", "compose"]
    return None


def test_root_env_example_uses_safe_portable_defaults() -> None:
    env_example = Path(".env.example").read_text()

    assert "LLM_PROVIDER=gemini" in env_example
    assert "MCP_TRANSPORT=streamable-http" in env_example
    assert "PAPER_LEDGER_DB_PATH=data/paper-ledger.db" in env_example
    assert "MARKET_DATA_DB_PATH=data/market-data.db" in env_example
    assert "PORTFOLIO_MARKET_DATA_PROVIDER=fixture" in env_example
    assert "# PORTFOLIO_MARKET_DATA_PROVIDER=json_file" in env_example
    assert "# PORTFOLIO_MARKET_DATA_JSON_PATH=data/market-snapshots.json" in env_example
    assert "PORTFOLIO_UNIVERSE_PROVIDER=fixture" in env_example
    assert "# PORTFOLIO_UNIVERSE_PROVIDER=json_file" in env_example
    assert "# PORTFOLIO_UNIVERSE_JSON_PATH=data/universes.json" in env_example
    assert "PORTFOLIO_FUNDAMENTALS_PROVIDER=fixture" in env_example
    assert "# PORTFOLIO_FUNDAMENTALS_PROVIDER=json_file" in env_example
    assert "# PORTFOLIO_FUNDAMENTALS_JSON_PATH=data/fundamentals.json" in env_example
    assert "OLLAMA_BASE_URL=http://ollama:11434" in env_example
    assert "FYERS" not in env_example.upper()


def test_dockerignore_excludes_local_references_and_env_files() -> None:
    dockerignore = Path(".dockerignore").read_text()

    for ignored in (
        ".env",
        ".env.*",
        "local/",
        "local-references/",
        "private-references/",
        "references/local/",
        "references/private/",
    ):
        assert ignored in dockerignore
    assert "!.env.example" in dockerignore


def test_compose_mounts_paper_ledger_volume() -> None:
    compose = Path("docker-compose.yml").read_text()

    assert "PAPER_LEDGER_DB_PATH: ${PAPER_LEDGER_DB_PATH:-/data/paper-ledger.db}" in compose
    assert "MARKET_DATA_DB_PATH: ${MARKET_DATA_DB_PATH:-/data/market-data.db}" in compose
    assert "PORTFOLIO_MARKET_DATA_PROVIDER: ${PORTFOLIO_MARKET_DATA_PROVIDER:-fixture}" in compose
    assert "PORTFOLIO_MARKET_DATA_JSON_PATH: ${PORTFOLIO_MARKET_DATA_JSON_PATH:-}" in compose
    assert "PORTFOLIO_UNIVERSE_PROVIDER: ${PORTFOLIO_UNIVERSE_PROVIDER:-fixture}" in compose
    assert "PORTFOLIO_UNIVERSE_JSON_PATH: ${PORTFOLIO_UNIVERSE_JSON_PATH:-}" in compose
    assert "PORTFOLIO_FUNDAMENTALS_PROVIDER: ${PORTFOLIO_FUNDAMENTALS_PROVIDER:-fixture}" in compose
    assert "PORTFOLIO_FUNDAMENTALS_JSON_PATH: ${PORTFOLIO_FUNDAMENTALS_JSON_PATH:-}" in compose
    assert "paper-ledger-data:/data" in compose
    assert "paper-ledger-data:" in compose


def test_compose_exposes_web_console() -> None:
    compose = Path("docker-compose.yml").read_text()

    assert "web:" in compose
    assert "dockerfile: apps/web/Dockerfile" in compose
    assert 'VITE_AGENT_API_URL: ${VITE_AGENT_API_URL:-http://localhost:8000}' in compose
    assert '"3000:3000"' in compose


def test_compose_config_is_valid_with_available_container_runtime() -> None:
    compose_command = _compose_command()
    if compose_command is None:
        pytest.skip("Docker or Podman is not installed.")

    result = subprocess.run(
        [*compose_command, "config", "--quiet"],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
