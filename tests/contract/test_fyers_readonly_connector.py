from __future__ import annotations

from pathlib import Path

import pytest

from portfolio_domain.fyers_readonly import (
    FyersReadOnlyConnector,
    normalize_fyers_symbol,
    parse_fyers_symbol,
)
from portfolio_mcp.tools import (
    EXPOSED_TOOL_NAMES,
    get_fyers_account_snapshot,
    get_fyers_connection_health,
    get_fyers_depth,
    get_fyers_instrument_metadata,
    get_fyers_ohlcv_history,
    get_fyers_option_chain,
    get_fyers_quote,
)
from portfolio_policy import ActionTier, classify_tool


def test_fyers_symbol_normalization_matches_reference_provider_mappings() -> None:
    assert normalize_fyers_symbol("infy") == "NSE:INFY-EQ"
    assert normalize_fyers_symbol("INFY.NS") == "NSE:INFY-EQ"
    assert normalize_fyers_symbol("INFY.BO") == "BSE:INFY-EQ"
    assert normalize_fyers_symbol("BSE:TCS-EQ") == "BSE:TCS-EQ"
    assert normalize_fyers_symbol("^NSEI") == "NSE:NIFTY50-INDEX"
    assert normalize_fyers_symbol("^CNX500") == "NSE:NIFTY500-INDEX"
    assert normalize_fyers_symbol("^UNKNOWN") == "NSE:UNKNOWN-INDEX"

    assert parse_fyers_symbol("NSE:INFY-EQ") == "INFY"
    assert parse_fyers_symbol("NSE:NIFTY50-INDEX") == "NIFTY50"


def test_fyers_fixture_connector_is_read_only_sanitized_and_preserves_signs() -> None:
    connector = FyersReadOnlyConnector.fixture()

    health = connector.connection_health().to_dict()
    quote = connector.get_quote("infy").to_dict()
    history = connector.get_ohlcv_history("INFY.NS").to_dict()
    depth = connector.get_depth("NSE:INFY-EQ").to_dict()
    metadata = connector.get_instrument_metadata("infy").to_dict()
    option_chain = connector.get_option_chain("^NSEI").to_dict()
    snapshot = connector.get_account_snapshot().to_dict()

    assert health["provider"] == "fyers"
    assert health["status"] == "fixture"
    assert health["credential_status"] == "not_loaded"
    assert "token" not in str(health).lower()

    assert quote["provider"] == "fyers"
    assert quote["symbol"] == "NSE:INFY-EQ"
    assert quote["status"] == "fresh"
    assert quote["source"] == "offline_fyers_fixture"
    assert history["symbol"] == "NSE:INFY-EQ"
    assert history["bars"][0]["open"] > 0
    assert history["provenance"]["symbol_format"] == "exchange_qualified"
    assert depth["symbol"] == "NSE:INFY-EQ"
    assert depth["bids"][0]["price"] < depth["asks"][0]["price"]
    assert metadata["exchange"] == "NSE"
    assert metadata["segment"] == "EQ"
    assert option_chain["underlying_symbol"] == "NSE:NIFTY50-INDEX"
    assert option_chain["contracts"][0]["symbol"].startswith("NSE:NIFTY")

    signed_positions = {item["symbol"]: item["signed_quantity"] for item in snapshot["positions"]}
    assert signed_positions["NSE:INFY-EQ"] == 12
    assert signed_positions["NSE:NIFTY50-INDEX"] == -1
    assert snapshot["funds"]["available_cash"] > 0
    assert snapshot["status"] == "fresh"
    assert "access_token" not in str(snapshot).lower()
    assert "auth_code" not in str(snapshot).lower()


def test_fyers_unknown_symbol_is_unavailable_not_yahoo_fallback() -> None:
    connector = FyersReadOnlyConnector.fixture()

    with pytest.raises(ValueError, match="No FYERS fixture quote"):
        connector.get_quote("missing-symbol")
    with pytest.raises(ValueError, match="No FYERS fixture OHLCV history"):
        connector.get_ohlcv_history("missing-symbol")
    with pytest.raises(ValueError, match="No FYERS fixture market depth"):
        connector.get_depth("missing-symbol")
    with pytest.raises(ValueError, match="No FYERS fixture instrument metadata"):
        connector.get_instrument_metadata("missing-symbol")
    with pytest.raises(ValueError, match="No FYERS fixture option chain"):
        connector.get_option_chain("missing-symbol")


def test_fyers_readonly_module_has_no_sdk_or_order_mutation_imports() -> None:
    source = Path("packages/domain/portfolio_domain/fyers_readonly.py").read_text().lower()

    forbidden_fragments = (
        "fyersmodel",
        "fyersbroker",
        "place_order",
        "modify_order",
        "cancel_order",
        "exit_positions",
        "generate_authcode",
        "access_token=",
        "yahoo",
    )
    for fragment in forbidden_fragments:
        assert fragment not in source


def test_fyers_mcp_tools_are_read_only_model_safe_and_sanitized() -> None:
    expected_tools = {
        "get_fyers_connection_health",
        "get_fyers_quote",
        "get_fyers_ohlcv_history",
        "get_fyers_depth",
        "get_fyers_instrument_metadata",
        "get_fyers_option_chain",
        "get_fyers_account_snapshot",
    }
    assert expected_tools.issubset(EXPOSED_TOOL_NAMES)
    for tool_name in expected_tools:
        assert classify_tool(tool_name) == ActionTier.READ_ONLY

    health = get_fyers_connection_health()
    quote = get_fyers_quote("infy")
    history = get_fyers_ohlcv_history("infy")
    depth = get_fyers_depth("infy")
    metadata = get_fyers_instrument_metadata("infy")
    option_chain = get_fyers_option_chain("^NSEI")
    account = get_fyers_account_snapshot()

    assert health["policy"]["tier"] == "read_only"
    assert quote["policy"]["tier"] == "read_only"
    assert history["policy"]["tier"] == "read_only"
    assert depth["policy"]["tier"] == "read_only"
    assert metadata["policy"]["tier"] == "read_only"
    assert option_chain["policy"]["tier"] == "read_only"
    assert account["policy"]["tier"] == "read_only"
    assert quote["quote"]["symbol"] == "NSE:INFY-EQ"
    assert history["history"]["symbol"] == "NSE:INFY-EQ"
    assert depth["depth"]["symbol"] == "NSE:INFY-EQ"
    assert metadata["metadata"]["symbol"] == "NSE:INFY-EQ"
    assert option_chain["option_chain"]["underlying_symbol"] == "NSE:NIFTY50-INDEX"
    assert account["snapshot"]["provider"] == "fyers"

    unavailable = get_fyers_option_chain("missing-symbol")
    assert unavailable["status"] == "unavailable"
    assert "empty" not in str(unavailable).lower()
    assert "zero" not in str(unavailable).lower()

    serialized = f"{health} {quote} {history} {depth} {metadata} {option_chain} {account}".lower()
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "password" not in serialized
    assert "place_order" not in serialized
