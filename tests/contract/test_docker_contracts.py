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
    assert "ENABLE_CLOUD_TELEMETRY=false" in env_example
    assert "MCP_TRANSPORT=streamable-http" in env_example
    assert "AGENT_TOOL_TRANSPORT=mcp" in env_example
    assert "AGENT_MCP_URL=http://mcp-server:8081/mcp" in env_example
    assert "PAPER_LEDGER_DB_PATH=data/paper-ledger.db" in env_example
    assert "PAPER_EXECUTION_KILL_SWITCH=false" in env_example
    assert "FYERS_CONNECTOR_KILL_SWITCH=false" in env_example
    assert "MARKET_DATA_DB_PATH=data/market-data.db" in env_example
    assert "PROVIDER_CONFIG_DB_PATH=data/provider-config.db" in env_example
    assert "PORTFOLIO_MARKET_DATA_PROVIDER=fixture" in env_example
    assert "# PORTFOLIO_MARKET_DATA_PROVIDER=json_file" in env_example
    assert "# PORTFOLIO_MARKET_DATA_JSON_PATH=data/market-snapshots.json" in env_example
    assert "PORTFOLIO_UNIVERSE_PROVIDER=fixture" in env_example
    assert "# PORTFOLIO_UNIVERSE_PROVIDER=json_file" in env_example
    assert "# PORTFOLIO_UNIVERSE_JSON_PATH=data/universes.json" in env_example
    assert "PORTFOLIO_FUNDAMENTALS_PROVIDER=fixture" in env_example
    assert "# PORTFOLIO_FUNDAMENTALS_PROVIDER=json_file" in env_example
    assert "# PORTFOLIO_FUNDAMENTALS_JSON_PATH=data/fundamentals.json" in env_example
    assert "PORTFOLIO_SENTIMENT_PROVIDER=fixture" in env_example
    assert "# PORTFOLIO_SENTIMENT_PROVIDER=json_file" in env_example
    assert "# PORTFOLIO_SENTIMENT_JSON_PATH=data/sentiment.json" in env_example
    assert "PORTFOLIO_VOLATILITY_PROVIDER=fixture" in env_example
    assert "# PORTFOLIO_VOLATILITY_PROVIDER=json_file" in env_example
    assert "# PORTFOLIO_VOLATILITY_JSON_PATH=data/volatility.json" in env_example
    assert "PORTFOLIO_MACRO_PROVIDER=fixture" in env_example
    assert "# PORTFOLIO_MACRO_PROVIDER=json_file" in env_example
    assert "# PORTFOLIO_MACRO_JSON_PATH=data/macro.json" in env_example
    assert "# LLM_MODEL=llama3.1:8b" in env_example
    assert "# OLLAMA_BASE_URL=http://host.containers.internal:11434" in env_example
    assert "# OLLAMA_IMAGE_TAG=0.32.3" in env_example
    assert "# OLLAMA_PREPULL_MODEL=llama3.1:8b" in env_example
    assert "# OLLAMA_MODEL_DIGEST=sha256:<pinned-local-model-digest>" in env_example
    assert "# OLLAMA_STATUS_TIMEOUT_SECONDS=1.5" in env_example
    assert "# OLLAMA_AVAILABLE_MODEL_DIGESTS=llama3.1:8b=sha256:<pinned-local-model-digest>" in env_example
    assert "# MODEL_TUNING_CANDIDATES=llama3.1:8b,gemma:7b,gemma4:12b" in env_example
    assert "FYERS_CLIENT_ID" not in env_example.upper()
    assert "FYERS_CLIENT_SECRET" not in env_example.upper()
    assert "FYERS_ACCESS_TOKEN" not in env_example.upper()
    assert "FYERS_REFRESH_TOKEN" not in env_example.upper()
    assert "FYERS_TRADING_TOKEN" not in env_example.upper()


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
    assert "PAPER_EXECUTION_KILL_SWITCH: ${PAPER_EXECUTION_KILL_SWITCH:-false}" in compose
    assert "FYERS_CONNECTOR_KILL_SWITCH: ${FYERS_CONNECTOR_KILL_SWITCH:-false}" in compose
    assert "ENABLE_CLOUD_TELEMETRY: ${ENABLE_CLOUD_TELEMETRY:-false}" in compose
    assert "MARKET_DATA_DB_PATH: ${MARKET_DATA_DB_PATH:-/data/market-data.db}" in compose
    assert "PROVIDER_CONFIG_DB_PATH: ${PROVIDER_CONFIG_DB_PATH:-/data/provider-config.db}" in compose
    assert "PORTFOLIO_MARKET_DATA_PROVIDER: ${PORTFOLIO_MARKET_DATA_PROVIDER:-fixture}" in compose
    assert "PORTFOLIO_MARKET_DATA_JSON_PATH: ${PORTFOLIO_MARKET_DATA_JSON_PATH:-}" in compose
    assert "PORTFOLIO_UNIVERSE_PROVIDER: ${PORTFOLIO_UNIVERSE_PROVIDER:-fixture}" in compose
    assert "PORTFOLIO_UNIVERSE_JSON_PATH: ${PORTFOLIO_UNIVERSE_JSON_PATH:-}" in compose
    assert "PORTFOLIO_FUNDAMENTALS_PROVIDER: ${PORTFOLIO_FUNDAMENTALS_PROVIDER:-fixture}" in compose
    assert "PORTFOLIO_FUNDAMENTALS_JSON_PATH: ${PORTFOLIO_FUNDAMENTALS_JSON_PATH:-}" in compose
    assert "PORTFOLIO_SENTIMENT_PROVIDER: ${PORTFOLIO_SENTIMENT_PROVIDER:-fixture}" in compose
    assert "PORTFOLIO_SENTIMENT_JSON_PATH: ${PORTFOLIO_SENTIMENT_JSON_PATH:-}" in compose
    assert "PORTFOLIO_VOLATILITY_PROVIDER: ${PORTFOLIO_VOLATILITY_PROVIDER:-fixture}" in compose
    assert "PORTFOLIO_VOLATILITY_JSON_PATH: ${PORTFOLIO_VOLATILITY_JSON_PATH:-}" in compose
    assert "PORTFOLIO_MACRO_PROVIDER: ${PORTFOLIO_MACRO_PROVIDER:-fixture}" in compose
    assert "PORTFOLIO_MACRO_JSON_PATH: ${PORTFOLIO_MACRO_JSON_PATH:-}" in compose
    assert "OLLAMA_BASE_URL: ${OLLAMA_BASE_URL:-http://host.containers.internal:11434}" in compose
    assert "OLLAMA_STATUS_TIMEOUT_SECONDS: ${OLLAMA_STATUS_TIMEOUT_SECONDS:-1.5}" in compose
    assert "OLLAMA_AVAILABLE_MODEL_DIGESTS: ${OLLAMA_AVAILABLE_MODEL_DIGESTS:-}" in compose
    assert "image: ollama/ollama:${OLLAMA_IMAGE_TAG:-0.32.3}" in compose
    assert "ollama-model-prepull:" in compose
    assert "OLLAMA_HOST: http://ollama:11434" in compose
    assert "OLLAMA_PREPULL_MODEL: ${OLLAMA_PREPULL_MODEL:-llama3.1:8b}" in compose
    assert "ollama pull \"$${OLLAMA_PREPULL_MODEL}\"" in compose
    assert "MODEL_CONTEXT_WINDOW_TOKENS: ${MODEL_CONTEXT_WINDOW_TOKENS:-8192}" in compose
    assert "MODEL_TUNING_CANDIDATES: ${MODEL_TUNING_CANDIDATES:-llama3.1:8b,gemma:7b,gemma4:12b}" in compose
    assert "AGENT_TOOL_TRANSPORT: ${AGENT_TOOL_TRANSPORT:-mcp}" in compose
    assert "AGENT_MCP_URL: ${AGENT_MCP_URL:-http://mcp-server:8081/mcp}" in compose
    assert '"11434:11434"' not in compose
    assert "paper-ledger-data:/data" in compose
    assert "paper-ledger-data:" in compose


def test_agent_service_image_includes_shared_runtime_packages() -> None:
    dockerfile = Path("apps/agent-service/Dockerfile").read_text()

    assert "COPY ./packages/capabilities ./packages/capabilities" in dockerfile
    assert "COPY ./packages/harness ./packages/harness" in dockerfile
    assert "COPY ./packages/model-provider ./packages/model-provider" in dockerfile


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
