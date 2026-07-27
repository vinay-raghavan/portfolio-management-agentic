from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

from .fyers_readonly import (
    BrokerAccountSnapshot,
    FyersDepthLevel,
    FyersFunds,
    FyersHolding,
    FyersInstrumentMetadata,
    FyersMarketDepth,
    FyersOhlcvBar,
    FyersOhlcvHistory,
    FyersOptionChain,
    FyersOptionContract,
    FyersOrderHistoryItem,
    FyersPosition,
    FyersQuote,
    normalize_fyers_symbol,
    parse_fyers_symbol,
)


class FyersSdkUnavailableError(RuntimeError):
    """Raised when the FYERS data API cannot provide an authoritative snapshot."""


class FyersSdkReadOnlyConnector:
    """Read-only FYERS SDK adapter with normalized, provenance-aware outputs."""

    def __init__(
        self,
        *,
        client_factory: Callable[[], Any],
        source_label: str = "fyers_sdk",
        now: Callable[[], str] | None = None,
        ttl: timedelta = timedelta(minutes=5),
    ) -> None:
        self._client_factory = client_factory
        self._source_label = source_label
        self._now = now or _utc_now
        self._ttl = ttl

    def get_quote(self, symbol: str) -> FyersQuote:
        normalized = normalize_fyers_symbol(symbol)
        response = self._client().quotes({"symbols": normalized})
        row = _first_quote_row(response, normalized)
        values = _mapping(row.get("v"))
        last_price = _positive_float(values.get("lp"))
        previous_close = _float_value(values.get("prev_close_price"))
        if last_price <= 0:
            raise FyersSdkUnavailableError(f"quote unavailable for {normalized}")
        fetched_at, expires_at = self._timestamps()
        return FyersQuote(
            provider="fyers",
            symbol=normalized,
            base_symbol=parse_fyers_symbol(normalized),
            status="fresh",
            source=self._source_label,
            as_of=fetched_at,
            fetched_at=fetched_at,
            expires_at=expires_at,
            last_price=last_price,
            previous_close=previous_close,
            day_change=round(last_price - previous_close, 2),
            day_change_pct=(
                round(((last_price - previous_close) / previous_close) * 100, 4)
                if previous_close
                else 0.0
            ),
            volume=int(_float_value(values.get("volume"))),
            bid=_float_value(values.get("bid")),
            ask=_float_value(values.get("ask")),
            provenance=_provenance("quotes"),
        )

    def get_ohlcv_history(
        self,
        symbol: str,
        *,
        resolution: str = "D",
        range_from: str | None = None,
        range_to: str | None = None,
    ) -> FyersOhlcvHistory:
        normalized = normalize_fyers_symbol(symbol)
        query = {
            "symbol": normalized,
            "resolution": resolution,
            "date_format": "0",
            "range_from": range_from or "",
            "range_to": range_to or "",
            "cont_flag": "1",
        }
        response = self._client().history(query)
        _require_success(response, f"OHLCV history unavailable for {normalized}")
        candles = response.get("candles")
        if not isinstance(candles, Sequence) or not candles:
            raise FyersSdkUnavailableError(f"OHLCV history unavailable for {normalized}")
        fetched_at, expires_at = self._timestamps()
        return FyersOhlcvHistory(
            provider="fyers",
            symbol=normalized,
            base_symbol=parse_fyers_symbol(normalized),
            status="fresh",
            source=self._source_label,
            as_of=fetched_at,
            fetched_at=fetched_at,
            expires_at=expires_at,
            timeframe=resolution,
            bars=[_bar_from_candle(candle) for candle in candles],
            provenance=_provenance("history"),
        )

    def get_depth(self, symbol: str) -> FyersMarketDepth:
        normalized = normalize_fyers_symbol(symbol)
        response = self._client().depth({"symbol": normalized})
        _require_success(response, f"depth unavailable for {normalized}")
        data = _mapping(response.get("d"))
        depth = _mapping(data.get(normalized))
        fetched_at, expires_at = self._timestamps()
        bids = [_depth_level(row) for row in _sequence(depth.get("bids"))]
        asks = [_depth_level(row) for row in _sequence(depth.get("ask") or depth.get("asks"))]
        if not bids or not asks:
            raise FyersSdkUnavailableError(f"depth unavailable for {normalized}")
        return FyersMarketDepth(
            provider="fyers",
            symbol=normalized,
            base_symbol=parse_fyers_symbol(normalized),
            status="fresh",
            source=self._source_label,
            as_of=fetched_at,
            fetched_at=fetched_at,
            expires_at=expires_at,
            bids=bids,
            asks=asks,
            provenance=_provenance("depth"),
        )

    def get_instrument_metadata(self, symbol: str) -> FyersInstrumentMetadata:
        quote = self.get_quote(symbol)
        exchange, segment = _exchange_segment(quote.symbol)
        return FyersInstrumentMetadata(
            provider="fyers",
            symbol=quote.symbol,
            base_symbol=quote.base_symbol,
            exchange=exchange,
            segment=segment,
            instrument_type=_instrument_type(segment),
            tick_size=0.05,
            lot_size=1,
            status=quote.status,
            source=quote.source,
            as_of=quote.as_of,
            fetched_at=quote.fetched_at,
            expires_at=quote.expires_at,
            provenance=_provenance("instrument_metadata"),
        )

    def get_option_chain(self, symbol: str) -> FyersOptionChain:
        normalized = normalize_fyers_symbol(symbol)
        response = self._client().optionchain(
            {
                "symbol": normalized,
                "strikecount": 10,
                "timestamp": "",
            }
        )
        _require_success(response, f"option chain unavailable for {normalized}")
        data = _mapping(response.get("data"))
        contracts = [_option_contract(row) for row in _sequence(data.get("optionsChain"))]
        if not contracts:
            raise FyersSdkUnavailableError(f"option chain unavailable for {normalized}")
        fetched_at, expires_at = self._timestamps()
        return FyersOptionChain(
            provider="fyers",
            underlying_symbol=normalized,
            base_symbol=parse_fyers_symbol(normalized),
            status="fresh",
            source=self._source_label,
            as_of=fetched_at,
            fetched_at=fetched_at,
            expires_at=expires_at,
            contracts=contracts,
            provenance=_provenance("optionchain"),
        )

    def get_account_snapshot(self) -> BrokerAccountSnapshot:
        holdings_response = self._client().holdings()
        _require_success(holdings_response, "holdings unavailable from FYERS")
        position_response = self._client().positions()
        _require_success(position_response, "positions unavailable from FYERS")
        funds_response = self._client().funds()
        _require_success(funds_response, "funds unavailable from FYERS")
        orders_response = self._client().orderbook()
        _require_success(orders_response, "order history unavailable from FYERS")
        trades_response = self._client().tradebook()
        _require_success(trades_response, "trade history unavailable from FYERS")

        fetched_at, expires_at = self._timestamps()
        return BrokerAccountSnapshot(
            provider="fyers",
            status="fresh",
            source=self._source_label,
            as_of=fetched_at,
            fetched_at=fetched_at,
            expires_at=expires_at,
            holdings=[
                _holding(row)
                for row in _sequence(holdings_response.get("holdings"))
            ],
            positions=[
                _position(row)
                for row in _sequence(position_response.get("netPositions"))
            ],
            funds=_funds(funds_response),
            orders=[
                _order_history_item(row)
                for row in _sequence(orders_response.get("orderBook"))
            ],
            trades=[_sanitized_trade(row) for row in _sequence(trades_response.get("tradeBook"))],
            provenance={
                **_provenance("account_snapshot"),
                "quantity_semantics": "signed_position_quantity",
            },
            notes=[
                "FYERS account data is normalized as read-only provider data.",
                "Provider account state remains separate from the simulated paper ledger.",
            ],
        )

    def _client(self) -> Any:
        return self._client_factory()

    def _timestamps(self) -> tuple[str, str]:
        fetched_at = self._now()
        expires_at = (
            datetime.fromisoformat(fetched_at).astimezone(UTC) + self._ttl
        ).replace(microsecond=0).isoformat()
        return fetched_at, expires_at


def build_fyers_sdk_client_factory(
    *,
    client_id: str,
    token: str,
    log_path: str = "",
) -> Callable[[], Any]:
    """Build the FYERS SDK client factory for protected connector workers."""

    def client_factory() -> Any:
        from fyers_apiv3 import fyersModel

        return fyersModel.FyersModel(
            client_id=client_id,
            token=token,
            is_async=False,
            log_path=log_path,
        )

    return client_factory


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _first_quote_row(response: Mapping[str, Any], symbol: str) -> Mapping[str, Any]:
    _require_success(response, f"quote unavailable for {symbol}")
    rows = _sequence(response.get("d"))
    for row in rows:
        mapping = _mapping(row)
        if str(mapping.get("n") or symbol).upper() == symbol:
            return mapping
    if rows:
        return _mapping(rows[0])
    raise FyersSdkUnavailableError(f"quote unavailable for {symbol}")


def _require_success(response: Mapping[str, Any], message: str) -> None:
    if int(response.get("code") or 0) != 200:
        raise FyersSdkUnavailableError(message)


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _float_value(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)


def _positive_float(value: Any) -> float:
    resolved = _float_value(value)
    return resolved if resolved > 0 else 0.0


def _bar_from_candle(candle: Any) -> FyersOhlcvBar:
    values = list(_sequence(candle))
    if len(values) < 6:
        raise FyersSdkUnavailableError("OHLCV history unavailable from FYERS")
    timestamp = datetime.fromtimestamp(int(values[0]), tz=UTC).isoformat()
    return FyersOhlcvBar(
        timestamp=timestamp,
        open=float(values[1]),
        high=float(values[2]),
        low=float(values[3]),
        close=float(values[4]),
        volume=int(values[5]),
    )


def _depth_level(row: Any) -> FyersDepthLevel:
    payload = _mapping(row)
    return FyersDepthLevel(
        price=_float_value(payload.get("price")),
        quantity=int(_float_value(payload.get("volume") or payload.get("quantity"))),
        orders=int(_float_value(payload.get("ord") or payload.get("orders"))),
    )


def _option_contract(row: Any) -> FyersOptionContract:
    payload = _mapping(row)
    return FyersOptionContract(
        symbol=str(payload["symbol"]),
        strike=_float_value(payload.get("strike_price") or payload.get("strike")),
        option_type=str(payload.get("option_type") or payload.get("optionType")),
        expiry=str(payload.get("expiry") or ""),
        last_price=_float_value(payload.get("ltp") or payload.get("last_price")),
        open_interest=int(_float_value(payload.get("oi") or payload.get("open_interest"))),
        volume=int(_float_value(payload.get("volume"))),
        source_status="fresh",
    )


def _holding(row: Any) -> FyersHolding:
    payload = _mapping(row)
    symbol = normalize_fyers_symbol(str(payload.get("symbol")))
    quantity = int(_float_value(payload.get("quantity") or payload.get("qty")))
    last_price = _float_value(payload.get("ltp") or payload.get("last_price"))
    market_value = _float_value(payload.get("marketVal") or payload.get("market_value"))
    if market_value == 0 and last_price:
        market_value = round(quantity * last_price, 2)
    return FyersHolding(
        symbol=symbol,
        signed_quantity=quantity,
        average_price=_float_value(payload.get("costPrice") or payload.get("average_price")),
        last_price=last_price,
        market_value=market_value,
        product_type=str(payload.get("product") or payload.get("productType") or ""),
        source_status="fresh",
    )


def _position(row: Any) -> FyersPosition:
    payload = _mapping(row)
    symbol = normalize_fyers_symbol(str(payload.get("symbol")))
    quantity = int(_float_value(payload.get("netQty") or payload.get("net_quantity")))
    average_price = (
        _float_value(payload.get("buyAvg"))
        if quantity >= 0
        else _float_value(payload.get("sellAvg"))
    )
    return FyersPosition(
        symbol=symbol,
        signed_quantity=quantity,
        side="short" if quantity < 0 else "long",
        average_price=average_price,
        last_price=_float_value(payload.get("ltp") or payload.get("last_price")),
        unrealized_pnl=_float_value(payload.get("pl") or payload.get("unrealized_pnl")),
        product_type=str(payload.get("productType") or payload.get("product") or ""),
        source_status="fresh",
    )


def _funds(response: Mapping[str, Any]) -> FyersFunds:
    rows = [_mapping(row) for row in _sequence(response.get("fund_limit"))]
    values = {str(row.get("title", "")).strip().lower(): _float_value(row.get("equityAmount")) for row in rows}
    available_cash = values.get("available balance", 0.0)
    used_margin = values.get("utilized amount", 0.0)
    opening_balance = values.get("clear balance", available_cash + used_margin)
    if not values:
        raise FyersSdkUnavailableError("funds unavailable from FYERS")
    return FyersFunds(
        currency="INR",
        available_cash=available_cash,
        used_margin=used_margin,
        opening_balance=opening_balance,
        source_status="fresh",
    )


def _order_history_item(row: Any) -> FyersOrderHistoryItem:
    payload = _mapping(row)
    raw_id = str(payload.get("id") or payload.get("order_id") or "")
    symbol = normalize_fyers_symbol(str(payload.get("symbol")))
    return FyersOrderHistoryItem(
        order_id_hash=_hash_identifier(raw_id),
        symbol=symbol,
        status=str(payload.get("status") or "").lower(),
        side=_side(payload.get("side")),
        quantity=int(_float_value(payload.get("qty") or payload.get("quantity"))),
        order_type=_order_type(payload.get("type") or payload.get("order_type")),
        created_at=str(payload.get("orderDateTime") or payload.get("created_at") or ""),
    )


def _sanitized_trade(row: Any) -> dict[str, Any]:
    payload = _mapping(row)
    return {
        "trade_id_hash": _hash_identifier(str(payload.get("id") or payload.get("trade_id") or "")),
        "symbol": normalize_fyers_symbol(str(payload.get("symbol"))),
        "side": _side(payload.get("side")),
        "quantity": int(_float_value(payload.get("qty") or payload.get("quantity"))),
        "price": _float_value(payload.get("tradedPrice") or payload.get("price")),
        "traded_at": str(payload.get("tradeDateTime") or payload.get("traded_at") or ""),
        "source_status": "fresh",
    }


def _hash_identifier(value: str) -> str:
    return f"sha256:{sha256(value.encode('utf-8')).hexdigest()}"


def _side(value: Any) -> str:
    text = str(value).lower()
    if text in {"-1", "sell"}:
        return "sell"
    return "buy"


def _order_type(value: Any) -> str:
    text = str(value).lower()
    return {"1": "limit", "2": "market", "3": "stop", "4": "stop_limit"}.get(text, text)


def _exchange_segment(symbol: str) -> tuple[str, str]:
    exchange, rest = symbol.split(":", 1)
    segment = rest.rsplit("-", 1)[1] if "-" in rest else "EQ"
    return exchange, segment


def _instrument_type(segment: str) -> str:
    if segment == "INDEX":
        return "index"
    if segment in {"CE", "PE"}:
        return "option"
    return "equity"


def _provenance(operation: str) -> dict[str, Any]:
    return {
        "provider": "fyers",
        "operation": operation,
        "symbol_format": "exchange_qualified",
        "sdk_dependency": "fyers-apiv3==3.1.14",
        "fallback": "disabled",
    }
