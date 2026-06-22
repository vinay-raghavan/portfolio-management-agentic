from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import replace
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
    PaperPortfolioAccounting,
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


def _approval_event(
    order_id: str,
    approved_by: str,
    approval_note: str,
) -> AuditEvent:
    reviewer = approved_by.strip()
    if not reviewer:
        raise ValueError("approved_by is required for paper simulation approval.")
    return AuditEvent(
        event_id=f"audit-approval-{order_id}",
        event_type="paper_order_approved",
        entity_type="paper_order",
        entity_id=order_id,
        message="Paper order simulation was approved by a human reviewer.",
        created_at=FIXTURE_TIMESTAMP,
        actor=reviewer,
        redacted_payload={
            "order_id": order_id,
            "approved_by": reviewer,
            "approval_note": approval_note.strip(),
            "mode": "paper",
            "live_trading": "forbidden",
        },
    )


def _fill_event(fill: PaperFill) -> AuditEvent:
    return AuditEvent(
        event_id=f"audit-{fill.fill_id}",
        event_type="paper_fill_simulated",
        entity_type="paper_fill",
        entity_id=fill.fill_id,
        message="Approved paper order was simulated as a paper fill.",
        created_at=fill.filled_at,
        actor="agent",
        redacted_payload={
            "fill_id": fill.fill_id,
            "order_id": fill.order_id,
            "symbol": fill.symbol,
            "side": fill.side,
            "quantity": fill.quantity,
            "fill_price": fill.fill_price,
            "mode": "paper",
            "live_trading": "forbidden",
        },
    )


def _resolve_fill_price(
    order: PaperOrder,
    fill_price: float | None,
    current_position: PaperPosition | None,
) -> float:
    resolved = fill_price
    if resolved is None:
        resolved = order.requested_price
    if resolved is None and current_position is not None:
        resolved = current_position.last_price
    if resolved is None or resolved <= 0:
        raise ValueError("A positive fill_price is required for simulated fills.")
    return round(resolved, 2)


def _build_fill(
    order: PaperOrder,
    fill_price: float,
) -> PaperFill:
    return PaperFill(
        fill_id=f"fill-{order.order_id}",
        order_id=order.order_id,
        symbol=order.symbol,
        side=order.side,
        quantity=order.quantity,
        fill_price=fill_price,
        filled_at=FIXTURE_TIMESTAMP,
        mode="paper",
        source=OFFLINE_SOURCE,
        notes=[
            "Simulated paper fill only.",
            "No broker API, live order, or trading credential was used.",
        ],
    )


def _apply_fill_to_position(
    current_position: PaperPosition | None,
    fill: PaperFill,
) -> PaperPosition:
    if fill.side == "buy":
        if current_position is None:
            return PaperPosition(
                symbol=fill.symbol,
                quantity=fill.quantity,
                average_price=fill.fill_price,
                last_price=fill.fill_price,
                mode="paper",
                source=OFFLINE_SOURCE,
                notes=["Created by simulated paper fill."],
            )
        new_quantity = current_position.quantity + fill.quantity
        new_average = round(
            (
                current_position.average_price * current_position.quantity
                + fill.fill_price * fill.quantity
            )
            / new_quantity,
            2,
        )
        return replace(
            current_position,
            quantity=new_quantity,
            average_price=new_average,
            last_price=fill.fill_price,
            notes=[
                *current_position.notes,
                f"Updated by simulated buy fill {fill.fill_id}.",
            ],
        )

    if current_position is None or current_position.quantity < fill.quantity:
        raise ValueError("Cannot simulate sell fill without sufficient paper position.")
    new_quantity = current_position.quantity - fill.quantity
    return replace(
        current_position,
        quantity=new_quantity,
        average_price=current_position.average_price if new_quantity else 0.0,
        last_price=fill.fill_price,
        notes=[
            *current_position.notes,
            f"Updated by simulated sell fill {fill.fill_id}.",
        ],
    )


def _build_accounting(
    positions: list[PaperPosition],
    orders: list[PaperOrder],
    fills: list[PaperFill],
) -> PaperPortfolioAccounting:
    return PaperPortfolioAccounting(
        currency="INR",
        source=OFFLINE_SOURCE,
        total_market_value=round(
            sum(position.market_value for position in positions),
            2,
        ),
        total_unrealized_pnl=round(
            sum(position.unrealized_pnl for position in positions),
            2,
        ),
        open_positions=sum(1 for position in positions if position.quantity != 0),
        pending_orders=sum(1 for order in orders if order.status == "pending_approval"),
        approved_orders=sum(1 for order in orders if order.status == "approved"),
        filled_orders=sum(1 for order in orders if order.status == "filled"),
        simulated_fills=len(fills),
        notes=[
            "Paper accounting is simulated and fixture-backed.",
            "No live broker order, account, or trading credential is used.",
        ],
    )


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
        self._fills: dict[str, PaperFill] = {}

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

    def approve_order_simulation(
        self,
        order_id: str,
        approved_by: str,
        approval_note: str = "",
    ) -> tuple[PaperOrder, ApprovalRequest, AuditEvent]:
        order = self._orders.get(order_id)
        if order is None:
            raise ValueError(f"Unknown paper order_id: {order_id}")
        approval = self._approvals.get(order.approval_request_id)
        if approval is None:
            raise ValueError(f"Missing approval request for order_id: {order_id}")
        event = _approval_event(order_id, approved_by, approval_note)
        if approval.status != "approved":
            approval = replace(approval, status="approved")
            self._approvals[approval.approval_id] = approval
        if order.status == "pending_approval":
            order = replace(order, status="approved")
            self._orders[order.order_id] = order
        if not any(item.event_id == event.event_id for item in self._audit_events):
            self._audit_events.append(event)
        return order, approval, event

    def simulate_approved_fill(
        self,
        order_id: str,
        fill_price: float | None = None,
    ) -> tuple[PaperFill, PaperOrder, PaperPosition, AuditEvent]:
        order = self._orders.get(order_id)
        if order is None:
            raise ValueError(f"Unknown paper order_id: {order_id}")
        approval = self._approvals.get(order.approval_request_id)
        if approval is None or approval.status != "approved":
            raise ValueError("Paper order simulation requires human approval first.")
        existing_fill = self._fills.get(f"fill-{order.order_id}")
        if existing_fill is not None:
            position = self._position_for_symbol(existing_fill.symbol)
            event = self._event_by_id(f"audit-{existing_fill.fill_id}")
            return existing_fill, order, position, event

        current_position = self._position_for_symbol(order.symbol, required=False)
        resolved_price = _resolve_fill_price(order, fill_price, current_position)
        fill = _build_fill(order, resolved_price)
        position = _apply_fill_to_position(current_position, fill)
        fill_event = _fill_event(fill)
        filled_order = replace(
            order,
            status="filled",
            filled_quantity=order.quantity,
            fill_ids=[fill.fill_id],
        )
        self._fills[fill.fill_id] = fill
        self._orders[filled_order.order_id] = filled_order
        self._upsert_position(position)
        self._audit_events.append(fill_event)
        return fill, filled_order, position, fill_event

    def list_orders(self) -> list[PaperOrder]:
        return list(self._orders.values())

    def list_fills(self) -> list[PaperFill]:
        return list(self._fills.values())

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

    def portfolio_accounting(self) -> PaperPortfolioAccounting:
        return _build_accounting(
            self.list_positions(),
            self.list_orders(),
            self.list_fills(),
        )

    def _event_for_order(self, order_id: str) -> AuditEvent:
        for event in self._audit_events:
            if event.entity_id == order_id:
                return event
        raise ValueError(f"Missing audit event for order_id: {order_id}")

    def _event_by_id(self, event_id: str) -> AuditEvent:
        for event in self._audit_events:
            if event.event_id == event_id:
                return event
        raise ValueError(f"Missing audit event: {event_id}")

    def _position_for_symbol(
        self,
        symbol: str,
        required: bool = True,
    ) -> PaperPosition | None:
        normalized_symbol = _normalize_symbol(symbol)
        for position in self._positions:
            if position.symbol == normalized_symbol:
                return position
        if required:
            raise ValueError(f"Missing paper position for symbol: {normalized_symbol}")
        return None

    def _upsert_position(self, position: PaperPosition) -> None:
        for index, existing in enumerate(self._positions):
            if existing.symbol == position.symbol:
                self._positions[index] = position
                return
        self._positions.append(position)


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

    def approve_order_simulation(
        self,
        order_id: str,
        approved_by: str,
        approval_note: str = "",
    ) -> tuple[PaperOrder, ApprovalRequest, AuditEvent]:
        event = _approval_event(order_id, approved_by, approval_note)
        with self._connect() as connection:
            order = self._get_order(connection, order_id)
            if order is None:
                raise ValueError(f"Unknown paper order_id: {order_id}")
            approval = self._get_approval(connection, order.approval_request_id)
            if approval is None:
                raise ValueError(f"Missing approval request for order_id: {order_id}")

            if approval.status != "approved":
                approval = replace(approval, status="approved")
                connection.execute(
                    """
                    update approval_requests
                    set status = ?
                    where approval_id = ?
                    """,
                    (approval.status, approval.approval_id),
                )
            if order.status == "pending_approval":
                order = replace(order, status="approved")
                connection.execute(
                    """
                    update paper_orders
                    set status = ?
                    where order_id = ?
                    """,
                    (order.status, order.order_id),
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

    def simulate_approved_fill(
        self,
        order_id: str,
        fill_price: float | None = None,
    ) -> tuple[PaperFill, PaperOrder, PaperPosition, AuditEvent]:
        with self._connect() as connection:
            order = self._get_order(connection, order_id)
            if order is None:
                raise ValueError(f"Unknown paper order_id: {order_id}")
            approval = self._get_approval(connection, order.approval_request_id)
            if approval is None or approval.status != "approved":
                raise ValueError("Paper order simulation requires human approval first.")

            fill_id = f"fill-{order.order_id}"
            existing_fill = self._get_fill(connection, fill_id)
            if existing_fill is not None:
                current_order = self._get_order(connection, order.order_id)
                current_position = self._get_position(connection, existing_fill.symbol)
                fill_event = self._get_audit_event(
                    connection,
                    f"audit-{existing_fill.fill_id}",
                )
                if current_order is None or current_position is None or fill_event is None:
                    raise ValueError("Persisted paper fill is missing related state.")
                return existing_fill, current_order, current_position, fill_event

            current_position = self._get_position(connection, order.symbol)
            resolved_price = _resolve_fill_price(order, fill_price, current_position)
            fill = _build_fill(order, resolved_price)
            position = _apply_fill_to_position(current_position, fill)
            fill_event = _fill_event(fill)
            filled_order = replace(
                order,
                status="filled",
                filled_quantity=order.quantity,
                fill_ids=[fill.fill_id],
            )
            connection.execute(
                """
                insert into paper_fills (
                    fill_id,
                    order_id,
                    symbol,
                    side,
                    quantity,
                    fill_price,
                    filled_at,
                    mode,
                    source,
                    notes_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fill.fill_id,
                    fill.order_id,
                    fill.symbol,
                    fill.side,
                    fill.quantity,
                    fill.fill_price,
                    fill.filled_at,
                    fill.mode,
                    fill.source,
                    _to_json(fill.notes),
                ),
            )
            connection.execute(
                """
                update paper_orders
                set status = ?,
                    filled_quantity = ?,
                    fill_ids_json = ?
                where order_id = ?
                """,
                (
                    filled_order.status,
                    filled_order.filled_quantity,
                    _to_json(filled_order.fill_ids),
                    filled_order.order_id,
                ),
            )
            self._upsert_position(connection, position)
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
                    fill_event.event_id,
                    fill_event.event_type,
                    fill_event.entity_type,
                    fill_event.entity_id,
                    fill_event.message,
                    fill_event.created_at,
                    fill_event.actor,
                    _to_json(fill_event.redacted_payload),
                ),
            )
            connection.commit()
        return fill, filled_order, position, fill_event

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

    def portfolio_accounting(self) -> PaperPortfolioAccounting:
        return _build_accounting(
            self.list_positions(),
            self.list_orders(),
            self.list_fills(),
        )

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

    def _get_fill(
        self,
        connection: sqlite3.Connection,
        fill_id: str,
    ) -> PaperFill | None:
        row = connection.execute(
            "select * from paper_fills where fill_id = ?",
            (fill_id,),
        ).fetchone()
        return _row_to_fill(row) if row is not None else None

    def _get_position(
        self,
        connection: sqlite3.Connection,
        symbol: str,
    ) -> PaperPosition | None:
        row = connection.execute(
            "select * from paper_positions where symbol = ?",
            (_normalize_symbol(symbol),),
        ).fetchone()
        return _row_to_position(row) if row is not None else None

    def _upsert_position(
        self,
        connection: sqlite3.Connection,
        position: PaperPosition,
    ) -> None:
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
            ) values (?, ?, ?, ?, ?, ?, ?, 50)
            on conflict(symbol) do update set
                quantity = excluded.quantity,
                average_price = excluded.average_price,
                last_price = excluded.last_price,
                mode = excluded.mode,
                source = excluded.source,
                notes_json = excluded.notes_json
            """,
            (
                position.symbol,
                position.quantity,
                position.average_price,
                position.last_price,
                position.mode,
                position.source,
                _to_json(position.notes),
            ),
        )


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


def approve_fixture_paper_order_simulation(
    order_id: str,
    approved_by: str,
    approval_note: str = "",
) -> tuple[PaperOrder, ApprovalRequest, AuditEvent]:
    return _PAPER_LEDGER_STORE.approve_order_simulation(
        order_id,
        approved_by,
        approval_note,
    )


def simulate_fixture_approved_paper_fill(
    order_id: str,
    fill_price: float | None = None,
) -> tuple[PaperFill, PaperOrder, PaperPosition, AuditEvent]:
    return _PAPER_LEDGER_STORE.simulate_approved_fill(order_id, fill_price)


def list_fixture_paper_orders() -> list[PaperOrder]:
    return _PAPER_LEDGER_STORE.list_orders()


def list_fixture_paper_fills() -> list[PaperFill]:
    return _PAPER_LEDGER_STORE.list_fills()


def list_fixture_paper_positions() -> list[PaperPosition]:
    return _PAPER_LEDGER_STORE.list_positions()


def list_fixture_approval_queue() -> list[ApprovalRequest]:
    return _PAPER_LEDGER_STORE.approval_queue()


def list_fixture_audit_events() -> list[AuditEvent]:
    return _PAPER_LEDGER_STORE.audit_events()


def get_fixture_paper_portfolio_accounting() -> PaperPortfolioAccounting:
    return _PAPER_LEDGER_STORE.portfolio_accounting()
