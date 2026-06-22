from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from .models import (
    ApprovalRequest,
    AuditEvent,
    BacktestRequest,
    BacktestResult,
    BacktestTrade,
    PaperFill,
    PaperOrder,
    PaperPosition,
)

OFFLINE_SOURCE = "offline_fixture"
FIXTURE_TIMESTAMP = "2026-06-22T09:15:00+05:30"
SUPPORTED_ORDER_SIDES = {"buy", "sell"}
SUPPORTED_ORDER_TYPES = {"market", "limit"}


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or "unknown"


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("Symbol is required.")
    return normalized


def _normalize_setup(setup: str) -> str:
    normalized = setup.strip().lower()
    if not normalized:
        raise ValueError("Setup is required.")
    return normalized


def _validate_date_window(start_date: str, end_date: str) -> None:
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError as exc:
        raise ValueError("Backtest dates must use YYYY-MM-DD format.") from exc
    if start > end:
        raise ValueError("Backtest start_date must be on or before end_date.")


def _fixture_positions() -> list[PaperPosition]:
    return [
        PaperPosition(
            symbol="TATAMOTORS",
            quantity=10,
            average_price=912.50,
            last_price=975.20,
            mode="paper",
            source=OFFLINE_SOURCE,
            notes=["Fixture paper position from a prior simulated fill."],
        ),
        PaperPosition(
            symbol="SBIN",
            quantity=20,
            average_price=805.00,
            last_price=821.40,
            mode="paper",
            source=OFFLINE_SOURCE,
            notes=["Fixture paper position used for exposure review."],
        ),
    ]


def _build_order_proposal_artifacts(
    strategy_id: str,
    symbol: str,
    side: str,
    quantity: int,
    order_type: str,
    requested_price: float | None,
) -> tuple[PaperOrder, ApprovalRequest, AuditEvent]:
    normalized_symbol = _normalize_symbol(symbol)
    normalized_side = side.strip().lower()
    normalized_order_type = order_type.strip().lower()
    if normalized_side not in SUPPORTED_ORDER_SIDES:
        raise ValueError("Paper order side must be buy or sell.")
    if normalized_order_type not in SUPPORTED_ORDER_TYPES:
        raise ValueError("Paper order type must be market or limit.")
    if quantity <= 0:
        raise ValueError("Paper order quantity must be greater than zero.")
    if requested_price is not None and requested_price <= 0:
        raise ValueError("Requested price must be greater than zero when provided.")

    normalized_strategy = strategy_id.strip()
    if not normalized_strategy:
        raise ValueError("Strategy id is required.")

    order_id = "-".join(
        (
            "paper-order",
            _slug(normalized_strategy),
            _slug(normalized_symbol),
            normalized_side,
            str(quantity),
            normalized_order_type,
        )
    )
    approval_id = f"approval-{order_id}"
    order = PaperOrder(
        order_id=order_id,
        strategy_id=normalized_strategy,
        symbol=normalized_symbol,
        side=normalized_side,
        quantity=quantity,
        order_type=normalized_order_type,
        mode="paper",
        status="pending_approval",
        requested_price=requested_price,
        filled_quantity=0,
        fill_ids=[],
        approval_request_id=approval_id,
        created_at=FIXTURE_TIMESTAMP,
        notes=[
            "Draft paper order only; no fill has been simulated.",
            "Human approval is required before any future simulated execution.",
            "Live broker order placement is forbidden.",
        ],
    )
    approval = ApprovalRequest(
        approval_id=approval_id,
        action_type="paper_order_simulation",
        status="pending",
        summary=(
            f"Review simulated {normalized_side} {quantity} "
            f"{normalized_symbol} order for strategy {normalized_strategy}."
        ),
        related_id=order_id,
        required_approval="human",
        requested_at=FIXTURE_TIMESTAMP,
        risk_notes=[
            "Confirm paper sizing, drawdown budget, and concentration before simulation.",
            "Approval cannot authorize live trading.",
        ],
    )
    event = AuditEvent(
        event_id=f"audit-{order_id}",
        event_type="paper_order_proposed",
        entity_type="paper_order",
        entity_id=order_id,
        message="Paper order proposal created and queued for human approval.",
        created_at=FIXTURE_TIMESTAMP,
        actor="agent",
        redacted_payload={
            "symbol": normalized_symbol,
            "side": normalized_side,
            "quantity": quantity,
            "order_type": normalized_order_type,
            "mode": "paper",
            "live_trading": "forbidden",
        },
    )
    return order, approval, event


class BacktestStore:
    """Deterministic offline backtest contract store."""

    def __init__(self) -> None:
        self._requests: dict[str, BacktestRequest] = {}

    def create_request(
        self,
        symbol: str,
        setup: str,
        start_date: str,
        end_date: str,
    ) -> BacktestRequest:
        normalized_symbol = _normalize_symbol(symbol)
        normalized_setup = _normalize_setup(setup)
        _validate_date_window(start_date, end_date)
        request_id = "-".join(
            (
                "backtest",
                _slug(normalized_symbol),
                _slug(normalized_setup),
                _slug(start_date),
                _slug(end_date),
            )
        )
        request = BacktestRequest(
            request_id=request_id,
            symbol=normalized_symbol,
            setup=normalized_setup,
            start_date=start_date,
            end_date=end_date,
            mode="paper",
            status="draft",
            source=OFFLINE_SOURCE,
            assumptions=[
                "Offline fixture bars and deterministic fills are used.",
                "Costs, slippage, taxes, and broker constraints are simplified.",
                "Position sizing is illustrative and capped for paper review.",
            ],
            notes=[
                "Backtest request is a simulation draft, not an order.",
                "Live trading is forbidden by policy.",
            ],
        )
        self._requests[request.request_id] = request
        return request

    def get_result(self, request_id: str) -> BacktestResult:
        request = self._requests.get(request_id)
        if request is None:
            raise ValueError(f"Unknown backtest request_id: {request_id}")

        trades = _fixture_trades(request.symbol, request.setup)
        total_pnl = round(sum(trade.pnl for trade in trades), 2)
        average_return = round(
            sum(trade.return_pct for trade in trades) / len(trades),
            2,
        )
        wins = [trade for trade in trades if trade.pnl > 0]
        metrics: dict[str, float | int | str] = {
            "trade_count": len(trades),
            "winning_trades": len(wins),
            "win_rate_pct": round(len(wins) / len(trades) * 100, 2),
            "total_pnl": total_pnl,
            "total_return_pct": round(total_pnl / 100000 * 100, 2),
            "average_trade_return_pct": average_return,
            "max_drawdown_pct": -3.4,
            "exposure_cap_pct": 8.0,
        }
        return BacktestResult(
            request_id=request.request_id,
            symbol=request.symbol,
            setup=request.setup,
            mode="paper",
            status="simulated",
            source=OFFLINE_SOURCE,
            metrics=metrics,
            trades=trades,
            warnings=[
                "Simulated backtest is not predictive and is not investment advice.",
                "No live order, broker API, or trading credential is used.",
            ],
            citations=[
                "breakout-continuation-v1",
                "volatility-regime-sizing-v1",
            ],
            generated_at=FIXTURE_TIMESTAMP,
        )


class PaperLedgerStore:
    """In-memory paper-only ledger used until durable persistence is added."""

    def __init__(self) -> None:
        self._orders: dict[str, PaperOrder] = {}
        self._approvals: dict[str, ApprovalRequest] = {}
        self._audit_events: list[AuditEvent] = []
        self._positions = _fixture_positions()

    def create_order_proposal(
        self,
        strategy_id: str,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        requested_price: float | None = None,
    ) -> tuple[PaperOrder, ApprovalRequest, AuditEvent]:
        order, approval, event = _build_order_proposal_artifacts(
            strategy_id,
            symbol,
            side,
            quantity,
            order_type,
            requested_price,
        )
        existing_order = self._orders.get(order.order_id)
        existing_approval = self._approvals.get(approval.approval_id)
        if existing_order is not None and existing_approval is not None:
            event = self._event_for_order(order.order_id)
            return existing_order, existing_approval, event

        self._orders[order.order_id] = order
        self._approvals[approval.approval_id] = approval
        self._audit_events.append(event)
        return order, approval, event

    def list_orders(self) -> list[PaperOrder]:
        return list(self._orders.values())

    def list_positions(self) -> list[PaperPosition]:
        return list(self._positions)

    def approval_queue(self) -> list[ApprovalRequest]:
        return [
            approval
            for approval in self._approvals.values()
            if approval.status == "pending"
        ]

    def audit_events(self) -> list[AuditEvent]:
        return list(self._audit_events)

    def _event_for_order(self, order_id: str) -> AuditEvent:
        for event in self._audit_events:
            if event.entity_id == order_id:
                return event
        raise ValueError(f"Missing audit event for order_id: {order_id}")


class SQLitePaperLedgerStore:
    """SQLite-backed paper-only ledger for local durable state."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        if self.db_path.parent != Path("."):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def create_order_proposal(
        self,
        strategy_id: str,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        requested_price: float | None = None,
    ) -> tuple[PaperOrder, ApprovalRequest, AuditEvent]:
        order, approval, event = _build_order_proposal_artifacts(
            strategy_id,
            symbol,
            side,
            quantity,
            order_type,
            requested_price,
        )
        with self._connect() as connection:
            existing_order = self._get_order(connection, order.order_id)
            existing_approval = self._get_approval(connection, approval.approval_id)
            existing_event = self._get_audit_event(connection, event.event_id)
            if (
                existing_order is not None
                and existing_approval is not None
                and existing_event is not None
            ):
                return existing_order, existing_approval, existing_event

            connection.execute(
                """
                insert into paper_orders (
                    order_id,
                    strategy_id,
                    symbol,
                    side,
                    quantity,
                    order_type,
                    mode,
                    status,
                    requested_price,
                    filled_quantity,
                    fill_ids_json,
                    approval_request_id,
                    created_at,
                    notes_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(order_id) do nothing
                """,
                (
                    order.order_id,
                    order.strategy_id,
                    order.symbol,
                    order.side,
                    order.quantity,
                    order.order_type,
                    order.mode,
                    order.status,
                    order.requested_price,
                    order.filled_quantity,
                    _to_json(order.fill_ids),
                    order.approval_request_id,
                    order.created_at,
                    _to_json(order.notes),
                ),
            )
            connection.execute(
                """
                insert into approval_requests (
                    approval_id,
                    action_type,
                    status,
                    summary,
                    related_id,
                    required_approval,
                    requested_at,
                    risk_notes_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(approval_id) do nothing
                """,
                (
                    approval.approval_id,
                    approval.action_type,
                    approval.status,
                    approval.summary,
                    approval.related_id,
                    approval.required_approval,
                    approval.requested_at,
                    _to_json(approval.risk_notes),
                ),
            )
            connection.execute(
                """
                insert into audit_events (
                    event_id,
                    event_type,
                    entity_type,
                    entity_id,
                    message,
                    created_at,
                    actor,
                    redacted_payload_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(event_id) do nothing
                """,
                (
                    event.event_id,
                    event.event_type,
                    event.entity_type,
                    event.entity_id,
                    event.message,
                    event.created_at,
                    event.actor,
                    _to_json(event.redacted_payload),
                ),
            )
            connection.commit()
        return order, approval, event

    def list_orders(self) -> list[PaperOrder]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select * from paper_orders
                order by created_at, order_id
                """
            ).fetchall()
        return [_row_to_order(row) for row in rows]

    def list_positions(self) -> list[PaperPosition]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select * from paper_positions
                order by sort_order, symbol
                """
            ).fetchall()
        return [_row_to_position(row) for row in rows]

    def approval_queue(self) -> list[ApprovalRequest]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select * from approval_requests
                where status = 'pending'
                order by requested_at, approval_id
                """
            ).fetchall()
        return [_row_to_approval(row) for row in rows]

    def audit_events(self) -> list[AuditEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select * from audit_events
                order by created_at, event_id
                """
            ).fetchall()
        return [_row_to_audit_event(row) for row in rows]

    def list_fills(self) -> list[PaperFill]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select * from paper_fills
                order by filled_at, fill_id
                """
            ).fetchall()
        return [_row_to_fill(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("pragma foreign_keys = on")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                create table if not exists paper_orders (
                    order_id text primary key,
                    strategy_id text not null,
                    symbol text not null,
                    side text not null check (side in ('buy', 'sell')),
                    quantity integer not null check (quantity > 0),
                    order_type text not null check (order_type in ('market', 'limit')),
                    mode text not null check (mode = 'paper'),
                    status text not null,
                    requested_price real,
                    filled_quantity integer not null default 0,
                    fill_ids_json text not null default '[]',
                    approval_request_id text not null,
                    created_at text not null,
                    notes_json text not null default '[]'
                );

                create table if not exists approval_requests (
                    approval_id text primary key,
                    action_type text not null,
                    status text not null,
                    summary text not null,
                    related_id text not null,
                    required_approval text not null,
                    requested_at text not null,
                    risk_notes_json text not null default '[]'
                );

                create table if not exists audit_events (
                    event_id text primary key,
                    event_type text not null,
                    entity_type text not null,
                    entity_id text not null,
                    message text not null,
                    created_at text not null,
                    actor text not null,
                    redacted_payload_json text not null default '{}'
                );

                create table if not exists paper_positions (
                    symbol text primary key,
                    quantity integer not null,
                    average_price real not null,
                    last_price real not null,
                    mode text not null check (mode = 'paper'),
                    source text not null,
                    notes_json text not null default '[]',
                    sort_order integer not null default 100
                );

                create table if not exists paper_fills (
                    fill_id text primary key,
                    order_id text not null,
                    symbol text not null,
                    side text not null check (side in ('buy', 'sell')),
                    quantity integer not null check (quantity > 0),
                    fill_price real not null,
                    filled_at text not null,
                    mode text not null check (mode = 'paper'),
                    source text not null,
                    notes_json text not null default '[]'
                );
                """
            )
            for sort_order, position in enumerate(_fixture_positions(), start=1):
                connection.execute(
                    """
                    insert into paper_positions (
                        symbol,
                        quantity,
                        average_price,
                        last_price,
                        mode,
                        source,
                        notes_json,
                        sort_order
                    ) values (?, ?, ?, ?, ?, ?, ?, ?)
                    on conflict(symbol) do nothing
                    """,
                    (
                        position.symbol,
                        position.quantity,
                        position.average_price,
                        position.last_price,
                        position.mode,
                        position.source,
                        _to_json(position.notes),
                        sort_order,
                    ),
                )
            connection.commit()

    def _get_order(
        self,
        connection: sqlite3.Connection,
        order_id: str,
    ) -> PaperOrder | None:
        row = connection.execute(
            "select * from paper_orders where order_id = ?",
            (order_id,),
        ).fetchone()
        return _row_to_order(row) if row is not None else None

    def _get_approval(
        self,
        connection: sqlite3.Connection,
        approval_id: str,
    ) -> ApprovalRequest | None:
        row = connection.execute(
            "select * from approval_requests where approval_id = ?",
            (approval_id,),
        ).fetchone()
        return _row_to_approval(row) if row is not None else None

    def _get_audit_event(
        self,
        connection: sqlite3.Connection,
        event_id: str,
    ) -> AuditEvent | None:
        row = connection.execute(
            "select * from audit_events where event_id = ?",
            (event_id,),
        ).fetchone()
        return _row_to_audit_event(row) if row is not None else None


def _to_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _from_json(value: str) -> Any:
    return json.loads(value)


def _row_to_order(row: sqlite3.Row) -> PaperOrder:
    return PaperOrder(
        order_id=row["order_id"],
        strategy_id=row["strategy_id"],
        symbol=row["symbol"],
        side=row["side"],
        quantity=row["quantity"],
        order_type=row["order_type"],
        mode=row["mode"],
        status=row["status"],
        requested_price=row["requested_price"],
        filled_quantity=row["filled_quantity"],
        fill_ids=list(_from_json(row["fill_ids_json"])),
        approval_request_id=row["approval_request_id"],
        created_at=row["created_at"],
        notes=list(_from_json(row["notes_json"])),
    )


def _row_to_approval(row: sqlite3.Row) -> ApprovalRequest:
    return ApprovalRequest(
        approval_id=row["approval_id"],
        action_type=row["action_type"],
        status=row["status"],
        summary=row["summary"],
        related_id=row["related_id"],
        required_approval=row["required_approval"],
        requested_at=row["requested_at"],
        risk_notes=list(_from_json(row["risk_notes_json"])),
    )


def _row_to_audit_event(row: sqlite3.Row) -> AuditEvent:
    return AuditEvent(
        event_id=row["event_id"],
        event_type=row["event_type"],
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        message=row["message"],
        created_at=row["created_at"],
        actor=row["actor"],
        redacted_payload=dict(_from_json(row["redacted_payload_json"])),
    )


def _row_to_position(row: sqlite3.Row) -> PaperPosition:
    return PaperPosition(
        symbol=row["symbol"],
        quantity=row["quantity"],
        average_price=row["average_price"],
        last_price=row["last_price"],
        mode=row["mode"],
        source=row["source"],
        notes=list(_from_json(row["notes_json"])),
    )


def _row_to_fill(row: sqlite3.Row) -> PaperFill:
    return PaperFill(
        fill_id=row["fill_id"],
        order_id=row["order_id"],
        symbol=row["symbol"],
        side=row["side"],
        quantity=row["quantity"],
        fill_price=row["fill_price"],
        filled_at=row["filled_at"],
        mode=row["mode"],
        source=row["source"],
        notes=list(_from_json(row["notes_json"])),
    )


def _fixture_trades(symbol: str, setup: str) -> list[BacktestTrade]:
    normalized_symbol = _normalize_symbol(symbol)
    normalized_setup = _normalize_setup(setup)
    return [
        BacktestTrade(
            trade_id=f"trade-{_slug(normalized_symbol)}-{_slug(normalized_setup)}-1",
            symbol=normalized_symbol,
            side="buy",
            entry_date="2026-02-05",
            exit_date="2026-02-20",
            quantity=10,
            entry_price=912.50,
            exit_price=948.20,
            pnl=357.00,
            return_pct=3.91,
            status="closed_simulated",
        ),
        BacktestTrade(
            trade_id=f"trade-{_slug(normalized_symbol)}-{_slug(normalized_setup)}-2",
            symbol=normalized_symbol,
            side="buy",
            entry_date="2026-04-03",
            exit_date="2026-04-18",
            quantity=8,
            entry_price=955.00,
            exit_price=932.40,
            pnl=-180.80,
            return_pct=-2.37,
            status="closed_simulated",
        ),
        BacktestTrade(
            trade_id=f"trade-{_slug(normalized_symbol)}-{_slug(normalized_setup)}-3",
            symbol=normalized_symbol,
            side="buy",
            entry_date="2026-05-10",
            exit_date="2026-06-07",
            quantity=8,
            entry_price=944.30,
            exit_price=986.10,
            pnl=334.40,
            return_pct=4.43,
            status="closed_simulated",
        ),
    ]


_BACKTEST_STORE = BacktestStore()


def build_paper_ledger_store() -> PaperLedgerStore | SQLitePaperLedgerStore:
    db_path = os.getenv("PAPER_LEDGER_DB_PATH", "").strip()
    if db_path:
        return SQLitePaperLedgerStore(db_path)
    return PaperLedgerStore()


_PAPER_LEDGER_STORE = build_paper_ledger_store()


def create_fixture_backtest_request(
    symbol: str,
    setup: str,
    start_date: str,
    end_date: str,
) -> BacktestRequest:
    return _BACKTEST_STORE.create_request(symbol, setup, start_date, end_date)


def get_fixture_backtest_result(request_id: str) -> BacktestResult:
    return _BACKTEST_STORE.get_result(request_id)


def create_fixture_paper_order_proposal(
    strategy_id: str,
    symbol: str,
    side: str,
    quantity: int,
    order_type: str = "market",
    requested_price: float | None = None,
) -> tuple[PaperOrder, ApprovalRequest, AuditEvent]:
    return _PAPER_LEDGER_STORE.create_order_proposal(
        strategy_id,
        symbol,
        side,
        quantity,
        order_type,
        requested_price,
    )


def list_fixture_paper_orders() -> list[PaperOrder]:
    return _PAPER_LEDGER_STORE.list_orders()


def list_fixture_paper_positions() -> list[PaperPosition]:
    return _PAPER_LEDGER_STORE.list_positions()


def list_fixture_approval_queue() -> list[ApprovalRequest]:
    return _PAPER_LEDGER_STORE.approval_queue()


def list_fixture_audit_events() -> list[AuditEvent]:
    return _PAPER_LEDGER_STORE.audit_events()
