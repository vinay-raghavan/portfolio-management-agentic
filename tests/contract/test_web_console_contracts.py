from __future__ import annotations

import json
from pathlib import Path


WEB_ROOT = Path("apps/web")


def test_web_console_package_declares_build_and_preview_scripts() -> None:
    package = json.loads((WEB_ROOT / "package.json").read_text())

    assert package["private"] is True
    assert package["scripts"]["build"] == "vite build"
    assert package["scripts"]["preview"] == "vite preview --host 0.0.0.0 --port 3000"
    assert "react" in package["dependencies"]
    assert "vite" in package["devDependencies"]


def test_web_console_has_product_surfaces_and_no_live_trade_copy() -> None:
    source = (WEB_ROOT / "src" / "App.tsx").read_text()

    for expected in (
        "Run pre-market briefing",
        "Review approval queue",
        "Generate paper report",
        "Focused workflow pages",
        "Screener preset",
        "Draft paper strategy",
        "Create backtest request",
        "Create paper order proposal",
        "Approve simulation",
        "Simulate paper fill",
        "Provider health",
        "Provider settings",
        "Provider profiles",
        "Import validation",
        "Import jobs",
        "Configured files",
        "Refresh profile",
        "Last validation",
        "Needs attention",
        "Screener candidates",
        "Paper Ledger",
        "Live trading blocked",
    ):
        assert expected in source

    assert "Place live order" not in source
    assert "broker token" not in source.lower()


def test_compose_exposes_web_console_without_secrets() -> None:
    compose = Path("docker-compose.yml").read_text()

    assert "web:" in compose
    assert "apps/web/Dockerfile" in compose
    assert '"3000:3000"' in compose
    assert "VITE_AGENT_API_URL" in compose
    assert "GOOGLE_API_KEY" not in compose.split("web:", 1)[1]
    assert "ANTHROPIC_API_KEY" not in compose.split("web:", 1)[1]
