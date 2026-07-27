from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


INDEX_SYMBOL_MAP: dict[str, str] = {
    "^NSEI": "NSE:NIFTY50-INDEX",
    "^BSESN": "BSE:SENSEX-INDEX",
    "^NSEBANK": "NSE:NIFTYBANK-INDEX",
    "^NSMIDCP": "NSE:NIFTYMIDCAP50-INDEX",
    "^NSEMDCP50": "NSE:NIFTYMIDCAP50-INDEX",
    "^CNXIT": "NSE:NIFTYIT-INDEX",
    "^CNX500": "NSE:NIFTY500-INDEX",
    "^CNXAUTO": "NSE:NIFTYAUTO-INDEX",
    "^CNXFIN": "NSE:NIFTYFINSERVICE-INDEX",
    "^CNXMETAL": "NSE:NIFTYMETAL-INDEX",
    "^CNXPHARMA": "NSE:NIFTYPHARMA-INDEX",
    "^CNXPSUBANK": "NSE:NIFTYPSUBANK-INDEX",
    "^CNXREALTY": "NSE:NIFTYREALTY-INDEX",
    "^CNXINFRA": "NSE:NIFTYINFRA-INDEX",
    "^CNXENERGY": "NSE:NIFTYENERGY-INDEX",
    "^CNXFMCG": "NSE:NIFTYFMCG-INDEX",
}


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def normalize_fyers_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("FYERS symbol is required.")
    if ":" in normalized:
        return normalized
    if normalized.startswith("^"):
        mapped = INDEX_SYMBOL_MAP.get(normalized)
        if mapped:
            return mapped
        base = normalized.lstrip("^").replace(".NS", "")
        return f"NSE:{base}-INDEX"
    if normalized.endswith(".NS"):
        return f"NSE:{normalized[:-3]}-EQ"
    if normalized.endswith(".BO"):
        return f"BSE:{normalized[:-3]}-EQ"
    return f"NSE:{normalized}-EQ"


def parse_fyers_symbol(symbol: str) -> str:
    base = symbol.strip().upper()
    if ":" in base:
        base = base.split(":", 1)[1]
    if "-" in base:
        base = base.split("-", 1)[0]
    return base


@dataclass(frozen=True)
class FyersConnectionHealth:
    provider: str
    status: str
    credential_status: str
    data_app_mode: str
    daily_auth_required: bool
    allowed_operations: list[str]
    source: str
    as_of: str
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FyersQuote:
    provider: str
    symbol: str
    base_symbol: str
    status: str
    source: str
    as_of: str
    fetched_at: str
    expires_at: str
    last_price: float
    previous_close: float
    day_change: float
    day_change_pct: float
    volume: int
    bid: float
    ask: float
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FyersOhlcvBar:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FyersOhlcvHistory:
    provider: str
    symbol: str
    base_symbol: str
    status: str
    source: str
    as_of: str
    fetched_at: str
    expires_at: str
    timeframe: str
    bars: list[FyersOhlcvBar]
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "symbol": self.symbol,
            "base_symbol": self.base_symbol,
            "status": self.status,
            "source": self.source,
            "as_of": self.as_of,
            "fetched_at": self.fetched_at,
            "expires_at": self.expires_at,
            "timeframe": self.timeframe,
            "bars": [bar.to_dict() for bar in self.bars],
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class FyersDepthLevel:
    price: float
    quantity: int
    orders: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FyersMarketDepth:
    provider: str
    symbol: str
    base_symbol: str
    status: str
    source: str
    as_of: str
    fetched_at: str
    expires_at: str
    bids: list[FyersDepthLevel]
    asks: list[FyersDepthLevel]
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "symbol": self.symbol,
            "base_symbol": self.base_symbol,
            "status": self.status,
            "source": self.source,
            "as_of": self.as_of,
            "fetched_at": self.fetched_at,
            "expires_at": self.expires_at,
            "bids": [level.to_dict() for level in self.bids],
            "asks": [level.to_dict() for level in self.asks],
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class FyersInstrumentMetadata:
    provider: str
    symbol: str
    base_symbol: str
    exchange: str
    segment: str
    instrument_type: str
    tick_size: float
    lot_size: int
    status: str
    source: str
    as_of: str
    fetched_at: str
    expires_at: str
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FyersOptionContract:
    symbol: str
    strike: float
    option_type: str
    expiry: str
    last_price: float
    open_interest: int
    volume: int
    source_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FyersOptionChain:
    provider: str
    underlying_symbol: str
    base_symbol: str
    status: str
    source: str
    as_of: str
    fetched_at: str
    expires_at: str
    contracts: list[FyersOptionContract]
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "underlying_symbol": self.underlying_symbol,
            "base_symbol": self.base_symbol,
            "status": self.status,
            "source": self.source,
            "as_of": self.as_of,
            "fetched_at": self.fetched_at,
            "expires_at": self.expires_at,
            "contracts": [contract.to_dict() for contract in self.contracts],
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class FyersFunds:
    currency: str
    available_cash: float
    used_margin: float
    opening_balance: float
    source_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FyersHolding:
    symbol: str
    signed_quantity: int
    average_price: float
    last_price: float
    market_value: float
    product_type: str
    source_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FyersPosition:
    symbol: str
    signed_quantity: int
    side: str
    average_price: float
    last_price: float
    unrealized_pnl: float
    product_type: str
    source_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FyersOrderHistoryItem:
    order_id_hash: str
    symbol: str
    status: str
    side: str
    quantity: int
    order_type: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BrokerAccountSnapshot:
    provider: str
    status: str
    source: str
    as_of: str
    fetched_at: str
    expires_at: str
    holdings: list[FyersHolding]
    positions: list[FyersPosition]
    funds: FyersFunds
    orders: list[FyersOrderHistoryItem]
    trades: list[dict[str, Any]]
    provenance: dict[str, Any]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status,
            "source": self.source,
            "as_of": self.as_of,
            "fetched_at": self.fetched_at,
            "expires_at": self.expires_at,
            "holdings": [holding.to_dict() for holding in self.holdings],
            "positions": [position.to_dict() for position in self.positions],
            "funds": self.funds.to_dict(),
            "orders": [item.to_dict() for item in self.orders],
            "trades": self.trades,
            "provenance": self.provenance,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ProviderSnapshotEnvelope:
    provider: str
    snapshot_type: str
    status: str
    source: str
    as_of: str
    fetched_at: str
    expires_at: str
    payload: dict[str, Any]
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FyersReadOnlyConnector:
    def __init__(
        self,
        quotes: dict[str, FyersQuote],
        histories: dict[str, FyersOhlcvHistory],
        depths: dict[str, FyersMarketDepth],
        metadata: dict[str, FyersInstrumentMetadata],
        option_chains: dict[str, FyersOptionChain],
        account_snapshot: BrokerAccountSnapshot,
        health: FyersConnectionHealth,
    ) -> None:
        self._quotes = quotes
        self._histories = histories
        self._depths = depths
        self._metadata = metadata
        self._option_chains = option_chains
        self._account_snapshot = account_snapshot
        self._health = health

    @classmethod
    def fixture(cls) -> FyersReadOnlyConnector:
        fetched_at = _utc_now()
        as_of = "2026-07-27T09:20:00+05:30"
        expires_at = (
            datetime.now(UTC).replace(microsecond=0) + timedelta(minutes=5)
        ).isoformat()
        source = "offline_fyers_fixture"
        quote_rows = [
            {
                "symbol": "NSE:INFY-EQ",
                "last_price": 1508.25,
                "previous_close": 1498.1,
                "volume": 2456700,
                "bid": 1508.0,
                "ask": 1508.5,
            },
            {
                "symbol": "NSE:NIFTY50-INDEX",
                "last_price": 24837.0,
                "previous_close": 24752.45,
                "volume": 0,
                "bid": 24836.8,
                "ask": 24837.2,
            },
        ]
        quotes = {
            row["symbol"]: FyersQuote(
                provider="fyers",
                symbol=row["symbol"],
                base_symbol=parse_fyers_symbol(row["symbol"]),
                status="fresh",
                source=source,
                as_of=as_of,
                fetched_at=fetched_at,
                expires_at=expires_at,
                last_price=row["last_price"],
                previous_close=row["previous_close"],
                day_change=round(row["last_price"] - row["previous_close"], 2),
                day_change_pct=round(
                    ((row["last_price"] - row["previous_close"]) / row["previous_close"])
                    * 100,
                    4,
                ),
                volume=row["volume"],
                bid=row["bid"],
                ask=row["ask"],
                provenance={
                    "symbol_format": "exchange_qualified",
                    "fixture_version": "fyers-readonly-fixture/v1",
                },
            )
            for row in quote_rows
        }
        histories = {
            "NSE:INFY-EQ": FyersOhlcvHistory(
                provider="fyers",
                symbol="NSE:INFY-EQ",
                base_symbol="INFY",
                status="fresh",
                source=source,
                as_of=as_of,
                fetched_at=fetched_at,
                expires_at=expires_at,
                timeframe="1D",
                bars=[
                    FyersOhlcvBar(
                        timestamp="2026-07-24T15:30:00+05:30",
                        open=1488.0,
                        high=1512.7,
                        low=1482.4,
                        close=1498.1,
                        volume=2315400,
                    ),
                    FyersOhlcvBar(
                        timestamp="2026-07-27T09:20:00+05:30",
                        open=1501.0,
                        high=1510.4,
                        low=1498.8,
                        close=1508.25,
                        volume=2456700,
                    ),
                ],
                provenance={
                    "symbol_format": "exchange_qualified",
                    "fixture_version": "fyers-readonly-fixture/v1",
                },
            )
        }
        depths = {
            "NSE:INFY-EQ": FyersMarketDepth(
                provider="fyers",
                symbol="NSE:INFY-EQ",
                base_symbol="INFY",
                status="fresh",
                source=source,
                as_of=as_of,
                fetched_at=fetched_at,
                expires_at=expires_at,
                bids=[
                    FyersDepthLevel(price=1508.0, quantity=420, orders=7),
                    FyersDepthLevel(price=1507.8, quantity=280, orders=4),
                ],
                asks=[
                    FyersDepthLevel(price=1508.5, quantity=360, orders=6),
                    FyersDepthLevel(price=1508.9, quantity=250, orders=3),
                ],
                provenance={
                    "symbol_format": "exchange_qualified",
                    "fixture_version": "fyers-readonly-fixture/v1",
                },
            )
        }
        metadata = {
            "NSE:INFY-EQ": FyersInstrumentMetadata(
                provider="fyers",
                symbol="NSE:INFY-EQ",
                base_symbol="INFY",
                exchange="NSE",
                segment="EQ",
                instrument_type="equity",
                tick_size=0.05,
                lot_size=1,
                status="fresh",
                source=source,
                as_of=as_of,
                fetched_at=fetched_at,
                expires_at=expires_at,
                provenance={
                    "symbol_format": "exchange_qualified",
                    "fixture_version": "fyers-readonly-fixture/v1",
                },
            ),
            "NSE:NIFTY50-INDEX": FyersInstrumentMetadata(
                provider="fyers",
                symbol="NSE:NIFTY50-INDEX",
                base_symbol="NIFTY50",
                exchange="NSE",
                segment="INDEX",
                instrument_type="index",
                tick_size=0.05,
                lot_size=1,
                status="fresh",
                source=source,
                as_of=as_of,
                fetched_at=fetched_at,
                expires_at=expires_at,
                provenance={
                    "symbol_format": "exchange_qualified",
                    "fixture_version": "fyers-readonly-fixture/v1",
                },
            ),
        }
        option_chains = {
            "NSE:NIFTY50-INDEX": FyersOptionChain(
                provider="fyers",
                underlying_symbol="NSE:NIFTY50-INDEX",
                base_symbol="NIFTY50",
                status="fresh",
                source=source,
                as_of=as_of,
                fetched_at=fetched_at,
                expires_at=expires_at,
                contracts=[
                    FyersOptionContract(
                        symbol="NSE:NIFTY26JUL24800CE",
                        strike=24800.0,
                        option_type="CE",
                        expiry="2026-07-30",
                        last_price=94.25,
                        open_interest=842100,
                        volume=30250,
                        source_status="fresh",
                    ),
                    FyersOptionContract(
                        symbol="NSE:NIFTY26JUL24800PE",
                        strike=24800.0,
                        option_type="PE",
                        expiry="2026-07-30",
                        last_price=61.4,
                        open_interest=801550,
                        volume=28700,
                        source_status="fresh",
                    ),
                ],
                provenance={
                    "symbol_format": "exchange_qualified",
                    "fixture_version": "fyers-readonly-fixture/v1",
                },
            )
        }
        holdings = [
            FyersHolding(
                symbol="NSE:INFY-EQ",
                signed_quantity=12,
                average_price=1456.2,
                last_price=1508.25,
                market_value=18099.0,
                product_type="CNC",
                source_status="fresh",
            )
        ]
        positions = [
            FyersPosition(
                symbol="NSE:INFY-EQ",
                signed_quantity=12,
                side="long",
                average_price=1456.2,
                last_price=1508.25,
                unrealized_pnl=624.6,
                product_type="CNC",
                source_status="fresh",
            ),
            FyersPosition(
                symbol="NSE:NIFTY50-INDEX",
                signed_quantity=-1,
                side="short",
                average_price=24890.0,
                last_price=24837.0,
                unrealized_pnl=53.0,
                product_type="INTRADAY",
                source_status="fresh",
            ),
        ]
        account_snapshot = BrokerAccountSnapshot(
            provider="fyers",
            status="fresh",
            source=source,
            as_of=as_of,
            fetched_at=fetched_at,
            expires_at=expires_at,
            holdings=holdings,
            positions=positions,
            funds=FyersFunds(
                currency="INR",
                available_cash=125000.0,
                used_margin=18250.0,
                opening_balance=143250.0,
                source_status="fresh",
            ),
            orders=[
                FyersOrderHistoryItem(
                    order_id_hash="sha256:fixture-paperless-001",
                    symbol="NSE:INFY-EQ",
                    status="complete",
                    side="buy",
                    quantity=12,
                    order_type="market",
                    created_at="2026-07-27T09:18:00+05:30",
                )
            ],
            trades=[],
            provenance={
                "fixture_version": "fyers-readonly-fixture/v1",
                "quantity_semantics": "signed_position_quantity",
            },
            notes=[
                "Offline fixture mirrors the normalized FYERS read surface.",
                "Paper ledger state remains separate from provider account data.",
            ],
        )
        health = FyersConnectionHealth(
            provider="fyers",
            status="fixture",
            credential_status="not_loaded",
            data_app_mode="read_only",
            daily_auth_required=True,
            allowed_operations=[
                "connection_profile_health",
                "quotes",
                "ohlcv_history",
                "depth",
                "instrument_metadata",
                "option_chains",
                "holdings",
                "signed_positions",
                "funds",
                "history_reads",
            ],
            source=source,
            as_of=fetched_at,
            notes=[
                "Fixture mode has no broker session.",
                "OAuth and disconnect flows stay outside model-visible tools.",
            ],
        )
        return cls(
            quotes=quotes,
            histories=histories,
            depths=depths,
            metadata=metadata,
            option_chains=option_chains,
            account_snapshot=account_snapshot,
            health=health,
        )

    def connection_health(self) -> FyersConnectionHealth:
        return self._health

    def get_quote(self, symbol: str) -> FyersQuote:
        normalized = normalize_fyers_symbol(symbol)
        quote = self._quotes.get(normalized)
        if quote is None:
            raise ValueError(f"No FYERS fixture quote for {normalized}")
        return quote

    def get_ohlcv_history(self, symbol: str) -> FyersOhlcvHistory:
        normalized = normalize_fyers_symbol(symbol)
        history = self._histories.get(normalized)
        if history is None:
            raise ValueError(f"No FYERS fixture OHLCV history for {normalized}")
        return history

    def get_depth(self, symbol: str) -> FyersMarketDepth:
        normalized = normalize_fyers_symbol(symbol)
        depth = self._depths.get(normalized)
        if depth is None:
            raise ValueError(f"No FYERS fixture market depth for {normalized}")
        return depth

    def get_instrument_metadata(self, symbol: str) -> FyersInstrumentMetadata:
        normalized = normalize_fyers_symbol(symbol)
        metadata = self._metadata.get(normalized)
        if metadata is None:
            raise ValueError(f"No FYERS fixture instrument metadata for {normalized}")
        return metadata

    def get_option_chain(self, symbol: str) -> FyersOptionChain:
        normalized = normalize_fyers_symbol(symbol)
        option_chain = self._option_chains.get(normalized)
        if option_chain is None:
            raise ValueError(f"No FYERS fixture option chain for {normalized}")
        return option_chain

    def get_account_snapshot(self) -> BrokerAccountSnapshot:
        return self._account_snapshot

    def get_quote_envelope(self, symbol: str) -> ProviderSnapshotEnvelope:
        quote = self.get_quote(symbol)
        return ProviderSnapshotEnvelope(
            provider="fyers",
            snapshot_type="quote",
            status=quote.status,
            source=quote.source,
            as_of=quote.as_of,
            fetched_at=quote.fetched_at,
            expires_at=quote.expires_at,
            payload=quote.to_dict(),
            provenance=quote.provenance,
        )


def get_fyers_readonly_connector() -> FyersReadOnlyConnector:
    return FyersReadOnlyConnector.fixture()
