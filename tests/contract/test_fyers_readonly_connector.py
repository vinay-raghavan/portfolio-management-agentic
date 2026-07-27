from __future__ import annotations

from pathlib import Path

import pytest

from portfolio_domain.fyers_readonly import (
    FyersReadOnlyConnector,
    normalize_fyers_symbol,
    parse_fyers_symbol,
)
from portfolio_domain.fyers_sdk_readonly import (
    FyersSdkReadOnlyConnector,
    FyersSdkUnavailableError,
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


class _FakeFyersSdkClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def quotes(self, data: dict) -> dict:
        self.calls.append(("quotes", data))
        return {
            "code": 200,
            "d": [
                {
                    "n": "NSE:INFY-EQ",
                    "v": {
                        "lp": 1508.25,
                        "prev_close_price": 1498.10,
                        "volume": 2456700,
                        "bid": 1508.0,
                        "ask": 1508.5,
                    },
                }
            ],
        }

    def history(self, data: dict) -> dict:
        self.calls.append(("history", data))
        return {
            "code": 200,
            "candles": [
                [1785123600, 1488.0, 1512.7, 1482.4, 1498.1, 2315400],
                [1785123900, 1501.0, 1510.4, 1498.8, 1508.25, 2456700],
            ],
        }

    def depth(self, data: dict) -> dict:
        self.calls.append(("depth", data))
        return {
            "code": 200,
            "d": {
                "NSE:INFY-EQ": {
                    "bids": [
                        {"price": 1508.0, "volume": 420, "ord": 7},
                    ],
                    "ask": [
                        {"price": 1508.5, "volume": 360, "ord": 6},
                    ],
                }
            },
        }

    def optionchain(self, data: dict) -> dict:
        self.calls.append(("optionchain", data))
        return {
            "code": 200,
            "data": {
                "optionsChain": [
                    {
                        "symbol": "NSE:NIFTY26JUL24800CE",
                        "strike_price": 24800,
                        "option_type": "CE",
                        "expiry": "2026-07-30",
                        "ltp": 94.25,
                        "oi": 842100,
                        "volume": 30250,
                    }
                ]
            },
        }

    def holdings(self) -> dict:
        self.calls.append(("holdings", {}))
        return {
            "code": 200,
            "holdings": [
                {
                    "symbol": "NSE:INFY-EQ",
                    "quantity": 12,
                    "costPrice": 1456.2,
                    "ltp": 1508.25,
                    "marketVal": 18099.0,
                    "product": "CNC",
                }
            ],
        }

    def positions(self) -> dict:
        self.calls.append(("positions", {}))
        return {
            "code": 200,
            "netPositions": [
                {
                    "symbol": "NSE:NIFTY50-INDEX",
                    "netQty": -1,
                    "buyAvg": 0,
                    "sellAvg": 24890.0,
                    "ltp": 24837.0,
                    "pl": 53.0,
                    "productType": "INTRADAY",
                }
            ],
        }

    def funds(self) -> dict:
        self.calls.append(("funds", {}))
        return {
            "code": 200,
            "fund_limit": [
                {"title": "Available Balance", "equityAmount": 125000.0},
                {"title": "Utilized Amount", "equityAmount": 18250.0},
                {"title": "Clear Balance", "equityAmount": 143250.0},
            ],
        }

    def orderbook(self) -> dict:
        self.calls.append(("orderbook", {}))
        return {
            "code": 200,
            "orderBook": [
                {
                    "id": "raw-order-id-never-return",
                    "symbol": "NSE:INFY-EQ",
                    "status": "complete",
                    "side": 1,
                    "qty": 12,
                    "type": 2,
                    "orderDateTime": "2026-07-27T09:18:00+05:30",
                }
            ],
        }

    def tradebook(self) -> dict:
        self.calls.append(("tradebook", {}))
        return {"code": 200, "tradeBook": []}


class _ErrorFyersSdkClient(_FakeFyersSdkClient):
    def quotes(self, data: dict) -> dict:
        self.calls.append(("quotes", data))
        return {"code": 429, "message": "rate limit"}

    def holdings(self) -> dict:
        self.calls.append(("holdings", {}))
        return {"code": 401, "message": "token expired"}


def test_fyers_sdk_dependency_is_pinned_for_isolated_connector() -> None:
    pyproject = Path("pyproject.toml").read_text()

    assert '"fyers-apiv3==3.1.14"' in pyproject


def test_fyers_sdk_readonly_connector_normalizes_read_allowlist_without_secrets() -> None:
    fake_client = _FakeFyersSdkClient()
    connector = FyersSdkReadOnlyConnector(
        client_factory=lambda: fake_client,
        source_label="fyers_sdk_test",
        now=lambda: "2026-07-27T09:20:00+00:00",
    )

    quote = connector.get_quote("infy")
    history = connector.get_ohlcv_history("INFY.NS", resolution="5")
    depth = connector.get_depth("NSE:INFY-EQ")
    metadata = connector.get_instrument_metadata("infy")
    option_chain = connector.get_option_chain("^NSEI")
    account = connector.get_account_snapshot()

    assert quote.symbol == "NSE:INFY-EQ"
    assert quote.status == "fresh"
    assert quote.source == "fyers_sdk_test"
    assert history.timeframe == "5"
    assert history.bars[0].open == 1488.0
    assert depth.bids[0].price == 1508.0
    assert metadata.exchange == "NSE"
    assert metadata.segment == "EQ"
    assert option_chain.contracts[0].option_type == "CE"
    assert account.status == "fresh"
    assert account.holdings[0].signed_quantity == 12
    assert account.positions[0].signed_quantity == -1
    assert account.funds.available_cash == 125000.0
    assert account.orders[0].order_id_hash.startswith("sha256:")
    assert "raw-order-id-never-return" not in str(account.to_dict())
    assert [name for name, _ in fake_client.calls] == [
        "quotes",
        "history",
        "depth",
        "quotes",
        "optionchain",
        "holdings",
        "positions",
        "funds",
        "orderbook",
        "tradebook",
    ]

    serialized = f"{quote.to_dict()} {history.to_dict()} {account.to_dict()}".lower()
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized
    assert "client_secret" not in serialized
    assert "trading_token" not in serialized


def test_fyers_sdk_readonly_connector_fails_unavailable_not_empty_or_yahoo_fallback() -> None:
    fake_client = _ErrorFyersSdkClient()
    connector = FyersSdkReadOnlyConnector(client_factory=lambda: fake_client)

    with pytest.raises(FyersSdkUnavailableError, match="quote unavailable"):
        connector.get_quote("infy")
    with pytest.raises(FyersSdkUnavailableError, match="holdings unavailable"):
        connector.get_account_snapshot()

    serialized_calls = str(fake_client.calls).lower()
    assert "yahoo" not in serialized_calls
    assert "empty" not in serialized_calls
    assert "zero" not in serialized_calls


def test_fyers_sdk_readonly_module_exposes_no_mutation_surface() -> None:
    source = Path("packages/domain/portfolio_domain/fyers_sdk_readonly.py").read_text().lower()

    forbidden_fragments = (
        "fyersbroker",
        "place_order",
        "modify_order",
        "cancel_order",
        "exit_positions",
        "generate_authcode",
        "generate_token",
        "set_access_token",
        "yahoo",
    )
    for fragment in forbidden_fragments:
        assert fragment not in source
